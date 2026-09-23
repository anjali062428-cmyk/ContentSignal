"""
Datasets and Data Management API Router.
Handles CSV upload, schema and readiness evaluation, capability detection,
canonical mapping, background ML jobs, synchronous analysis, and dataset lifecycle.
Supports both isolated FlyRank safety rules and generic tabular datasets.
"""
import io
import json
import uuid
from pathlib import Path
from typing import List, Optional, Dict, Any
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status, BackgroundTasks, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.database import get_db, SessionLocal
from backend.models import Dataset, Page, PageMetric, Opportunity, Recommendation, User, AnalysisJob
from backend.auth import get_current_user, get_optional_current_user
from backend.schemas import (
    DatasetSummary,
    DatasetDetailResponse,
    ValidationSummaryResponse,
    AnalyzeDatasetResponse,
    AnalysisJobResponse,
    PaginatedOpportunities,
    OpportunityQueueItem,
    OverviewKPIs,
)
from content_engine.config import BASE_DIR
from content_engine.validation.dataset_validator import validate_dataset
from content_engine.scoring.dataset_analyzer import analyze_and_persist_dataset
from content_engine.capabilities.profiler import profile_dataset
from content_engine.capabilities.detector import detect_dataset_capabilities
from content_engine.readiness.checker import evaluate_dataset_readiness
from content_engine.canonical.mapper import map_dataframe_to_canonical

router = APIRouter(prefix="/api/datasets", tags=["Dataset Management"])

UPLOADS_DIR = BASE_DIR / "data" / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


def execute_analysis_job_task(job_id: str, dataset_id: str):
    db = SessionLocal()
    try:
        job = db.query(AnalysisJob).filter(AnalysisJob.job_id == job_id).first()
        if not job:
            return

        job.status = "PROCESSING"
        job.progress_pct = 20
        job.stage_label = "Verifying dataset schema, capabilities, and readiness..."
        db.commit()

        csv_path = UPLOADS_DIR / f"{dataset_id}.csv"
        if not csv_path.exists():
            ds = db.query(Dataset).filter(Dataset.dataset_id == dataset_id).first()
            if ds and (ds.is_starter or dataset_id == "starter-flyrank"):
                from content_engine.config import RAW_DATA_PATH
                csv_path = RAW_DATA_PATH
            else:
                raise FileNotFoundError(f"Stored dataset CSV file not found on disk at {csv_path}.")

        df_clean = pd.read_csv(csv_path)

        job.progress_pct = 50
        job.stage_label = "Executing model training/inference & opportunity scoring..."
        db.commit()

        job.progress_pct = 75
        job.stage_label = "Attributing capability-grounded reasons and action directives..."
        db.commit()

        analyze_and_persist_dataset(dataset_id=dataset_id, df_clean=df_clean, db=db)

        job.progress_pct = 95
        job.stage_label = "Synthesizing content archetypes and priority queues..."
        db.commit()

        job.status = "COMPLETED"
        job.progress_pct = 100
        job.stage_label = "Dataset processing complete. Insights ready."
        db.commit()
    except Exception as e:
        job = db.query(AnalysisJob).filter(AnalysisJob.job_id == job_id).first()
        if job:
            job.status = "FAILED"
            job.stage_label = "Analysis failed."
            job.error_message = str(e)
            db.commit()
    finally:
        db.close()


def _get_dataset_csv_path(ds: Dataset) -> Path:
    csv_path = UPLOADS_DIR / f"{ds.dataset_id}.csv"
    if not csv_path.exists():
        if ds.is_starter or ds.dataset_id == "starter-flyrank":
            from content_engine.config import RAW_DATA_PATH
            csv_path = RAW_DATA_PATH
        else:
            raise HTTPException(status_code=404, detail=f"Stored dataset CSV file not found on disk at {csv_path}.")
    return csv_path


@router.get("", response_model=List[DatasetSummary])
@router.get("/", response_model=List[DatasetSummary])
def list_datasets(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """
    Returns all accessible datasets.
    Always includes the permanent FlyRank Starter Dataset.
    """
    query = db.query(Dataset)
    if current_user:
        query = query.filter((Dataset.is_starter == True) | (Dataset.user_id == current_user.id) | (Dataset.user_id == None))
    
    datasets = query.order_by(desc(Dataset.is_starter), desc(Dataset.created_at)).all()
    return datasets


@router.get("/{dataset_id}", response_model=DatasetDetailResponse)
def get_dataset(dataset_id: str, db: Session = Depends(get_db)):
    """Retrieves dataset metadata, validation, capabilities, and readiness summary."""
    ds = db.query(Dataset).filter(Dataset.dataset_id == dataset_id).first()
    if not ds:
        raise HTTPException(status_code=404, detail=f"Dataset '{dataset_id}' not found.")
    
    def parse_json(val):
        if not val:
            return None
        try:
            return json.loads(val)
        except Exception:
            return None

    return {
        "id": ds.id,
        "dataset_id": ds.dataset_id,
        "name": ds.name,
        "user_id": ds.user_id,
        "is_starter": ds.is_starter,
        "row_count": ds.row_count,
        "column_count": ds.column_count,
        "validation_status": ds.validation_status,
        "model_name": ds.model_name,
        "created_at": ds.created_at,
        "updated_at": ds.updated_at,
        "validation_details": parse_json(ds.validation_details),
        "profile_details": parse_json(ds.profile_details),
        "capabilities_details": parse_json(ds.capabilities_details),
        "readiness_details": parse_json(ds.readiness_details),
        "mapping_details": parse_json(ds.mapping_details),
        "model_report_details": parse_json(ds.model_report_details),
    }


@router.get("/{dataset_id}/profile")
def get_dataset_profile(dataset_id: str, db: Session = Depends(get_db)):
    """Retrieves or dynamically computes the dataset metadata profile."""
    ds = db.query(Dataset).filter(Dataset.dataset_id == dataset_id).first()
    if not ds:
        raise HTTPException(status_code=404, detail=f"Dataset '{dataset_id}' not found.")
    
    if ds.profile_details:
        try:
            return json.loads(ds.profile_details)
        except Exception:
            pass

    csv_path = _get_dataset_csv_path(ds)
    profile = profile_dataset(csv_path)
    ds.profile_details = json.dumps(profile)
    db.commit()
    return profile


@router.get("/{dataset_id}/capabilities")
def get_dataset_capabilities(dataset_id: str, db: Session = Depends(get_db)):
    """Retrieves detected semantic capabilities and column mappings for a dataset."""
    ds = db.query(Dataset).filter(Dataset.dataset_id == dataset_id).first()
    if not ds:
        raise HTTPException(status_code=404, detail=f"Dataset '{dataset_id}' not found.")
    
    if ds.capabilities_details:
        try:
            return json.loads(ds.capabilities_details)
        except Exception:
            pass

    csv_path = _get_dataset_csv_path(ds)
    profile = profile_dataset(csv_path)
    capabilities = detect_dataset_capabilities(
        columns=profile.get("columns", []),
        dtypes=profile.get("dtypes", {}),
        is_wide_time_series=profile.get("is_wide_time_series", False),
    )
    ds.capabilities_details = json.dumps(capabilities)
    db.commit()
    return capabilities


@router.get("/{dataset_id}/readiness")
def get_dataset_readiness(dataset_id: str, db: Session = Depends(get_db)):
    """Retrieves the 10-point Dataset Readiness Checklist for a dataset."""
    ds = db.query(Dataset).filter(Dataset.dataset_id == dataset_id).first()
    if not ds:
        raise HTTPException(status_code=404, detail=f"Dataset '{dataset_id}' not found.")
    
    if ds.readiness_details:
        try:
            return json.loads(ds.readiness_details)
        except Exception:
            pass

    csv_path = _get_dataset_csv_path(ds)
    profile = profile_dataset(csv_path)
    capabilities = detect_dataset_capabilities(
        columns=profile.get("columns", []),
        dtypes=profile.get("dtypes", {}),
        is_wide_time_series=profile.get("is_wide_time_series", False),
    )
    readiness = evaluate_dataset_readiness(profile, capabilities)
    ds.readiness_details = json.dumps(readiness)
    db.commit()
    return readiness


@router.get("/{dataset_id}/mapping")
def get_dataset_mapping(dataset_id: str, db: Session = Depends(get_db)):
    """Retrieves canonical column mappings with confidence scores for a dataset."""
    ds = db.query(Dataset).filter(Dataset.dataset_id == dataset_id).first()
    if not ds:
        raise HTTPException(status_code=404, detail=f"Dataset '{dataset_id}' not found.")
    
    if ds.mapping_details:
        try:
            return json.loads(ds.mapping_details)
        except Exception:
            pass

    csv_path = _get_dataset_csv_path(ds)
    df = pd.read_csv(csv_path, nrows=50)
    mappings, _ = map_dataframe_to_canonical(df)
    ds.mapping_details = json.dumps(mappings)
    db.commit()
    return mappings


@router.get("/{dataset_id}/model")
def get_dataset_model_report(dataset_id: str, db: Session = Depends(get_db)):
    """Retrieves the dataset-specific model evaluation report."""
    ds = db.query(Dataset).filter(Dataset.dataset_id == dataset_id).first()
    if not ds:
        raise HTTPException(status_code=404, detail=f"Dataset '{dataset_id}' not found.")
    
    if ds.model_report_details:
        try:
            return json.loads(ds.model_report_details)
        except Exception:
            pass

    if ds.is_starter or dataset_id == "starter-flyrank":
        report_file = BASE_DIR / "reports" / "model_report.json"
        if report_file.exists():
            try:
                with open(report_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass

    return {
        "dataset_id": dataset_id,
        "model_type": ds.model_name or "Standard Model",
        "status": "Trained and operational",
        "features": ds.column_count,
        "training_rows": ds.row_count,
    }


@router.post("/upload", response_model=ValidationSummaryResponse)
async def upload_dataset(
    file: UploadFile = File(...),
    name: Optional[str] = Form(None),
    target: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """
    Uploads a CSV file, runs profiling, capability detection, readiness checks,
    canonical mapping, and registers the dataset.
    """
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="Invalid file format. Only CSV files (.csv) are accepted.",
        )

    content_bytes = await file.read()
    if len(content_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded CSV file is completely empty.")

    # Read CSV
    try:
        df_raw = pd.read_csv(io.BytesIO(content_bytes), encoding="utf-8")
    except UnicodeDecodeError:
        df_raw = pd.read_csv(io.BytesIO(content_bytes), encoding="latin-1")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse CSV file: {str(e)}")

    # Run dual-mode schema validation & readiness checks
    is_valid, summary, clean_df = validate_dataset(df_raw, explicit_target=target)

    dataset_name = (name or file.filename.rsplit(".", 1)[0]).strip()
    dataset_id = f"ds_{uuid.uuid4().hex[:10]}"

    # Save CSV
    save_df = clean_df if (clean_df is not None) else df_raw
    csv_file_path = UPLOADS_DIR / f"{dataset_id}.csv"
    save_df.to_csv(csv_file_path, index=False)

    # Persist dataset record
    user_id = current_user.id if current_user else None
    dataset_rec = Dataset(
        dataset_id=dataset_id,
        name=dataset_name,
        user_id=user_id,
        is_starter=False,
        row_count=summary["row_count"],
        column_count=summary["column_count"],
        validation_status="valid" if is_valid else "invalid",
        validation_details=json.dumps(summary),
        capabilities_details=json.dumps(summary.get("capabilities", {})),
        readiness_details=json.dumps(summary.get("readiness", {})),
        mapping_details=json.dumps(summary.get("mapping", [])),
        model_name="Gradient Boosting (Champion)" if is_valid and summary.get("adapter_type") == "FlyRankAdapter" else ("Dataset-Specific Classifier / Percentile" if is_valid else None),
    )
    db.add(dataset_rec)
    db.commit()
    db.refresh(dataset_rec)

    summary["dataset_id"] = dataset_id
    return summary


@router.post("/{dataset_id}/jobs", response_model=AnalysisJobResponse)
def create_analysis_job(
    dataset_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """
    Creates a background processing job for a dataset with progress tracking.
    """
    ds = db.query(Dataset).filter(Dataset.dataset_id == dataset_id).first()
    if not ds:
        raise HTTPException(status_code=404, detail=f"Dataset '{dataset_id}' not found.")

    if ds.validation_status == "invalid":
        raise HTTPException(
            status_code=400,
            detail="Cannot analyze dataset with invalid status. Please resolve readiness errors.",
        )

    job_id = f"job_{uuid.uuid4().hex[:12]}"
    user_id = current_user.id if current_user else None

    job = AnalysisJob(
        job_id=job_id,
        dataset_id=dataset_id,
        user_id=user_id,
        status="QUEUED",
        progress_pct=5,
        stage_label="Queued for analysis...",
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    background_tasks.add_task(execute_analysis_job_task, job_id, dataset_id)

    return AnalysisJobResponse(
        job_id=job.job_id,
        dataset_id=job.dataset_id,
        status=job.status,
        progress_pct=job.progress_pct,
        stage_label=job.stage_label,
        error_message=job.error_message,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


@router.get("/{dataset_id}/jobs/{job_id}", response_model=AnalysisJobResponse)
def get_analysis_job(
    dataset_id: str,
    job_id: str,
    db: Session = Depends(get_db),
):
    job = db.query(AnalysisJob).filter(AnalysisJob.job_id == job_id, AnalysisJob.dataset_id == dataset_id).first()
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")
    return AnalysisJobResponse(
        job_id=job.job_id,
        dataset_id=job.dataset_id,
        status=job.status,
        progress_pct=job.progress_pct,
        stage_label=job.stage_label,
        error_message=job.error_message,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


@router.get("/{dataset_id}/jobs", response_model=List[AnalysisJobResponse])
def list_analysis_jobs(
    dataset_id: str,
    limit: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db),
):
    jobs = (
        db.query(AnalysisJob)
        .filter(AnalysisJob.dataset_id == dataset_id)
        .order_by(desc(AnalysisJob.created_at))
        .limit(limit)
        .all()
    )
    return [
        AnalysisJobResponse(
            job_id=j.job_id,
            dataset_id=j.dataset_id,
            status=j.status,
            progress_pct=j.progress_pct,
            stage_label=j.stage_label,
            error_message=j.error_message,
            created_at=j.created_at,
            updated_at=j.updated_at,
        )
        for j in jobs
    ]


@router.post("/{dataset_id}/analyze", response_model=AnalyzeDatasetResponse)
def analyze_dataset(dataset_id: str, db: Session = Depends(get_db)):
    """
    Executes ML inference/training, opportunity scoring, reason engine, and archetype clustering
    on a previously validated dataset synchronously.
    """
    ds = db.query(Dataset).filter(Dataset.dataset_id == dataset_id).first()
    if not ds:
        raise HTTPException(status_code=404, detail=f"Dataset '{dataset_id}' not found.")

    if ds.validation_status == "invalid":
        raise HTTPException(
            status_code=400,
            detail="Cannot analyze dataset with invalid status. Please review and resolve readiness errors.",
        )

    csv_path = _get_dataset_csv_path(ds)
    df_clean = pd.read_csv(csv_path)
    try:
        result = analyze_and_persist_dataset(dataset_id=dataset_id, df_clean=df_clean, db=db)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Dataset analysis failed: {str(e)}")


@router.get("/{dataset_id}/opportunities", response_model=PaginatedOpportunities)
def get_dataset_opportunities(
    dataset_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    priority: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Returns paginated opportunity items for the specified dataset."""
    query = db.query(Opportunity, Page, PageMetric).join(
        Page, Opportunity.page_id == Page.page_id
    ).outerjoin(
        PageMetric, Page.page_id == PageMetric.page_id
    ).filter(Opportunity.dataset_id == dataset_id)

    if priority:
        query = query.filter(Opportunity.priority == priority.upper())
    if action:
        query = query.filter(Opportunity.action == action.upper())

    total = query.count()
    items_raw = query.order_by(Opportunity.queue_rank.asc()).offset((page - 1) * limit).limit(limit).all()

    items = []
    for opp, pg, met in items_raw:
        items.append(OpportunityQueueItem(
            queue_rank=opp.queue_rank,
            page_id=opp.page_id,
            client_id=pg.client_id,
            opportunity_score=opp.opportunity_score,
            priority=opp.priority,
            action=opp.action,
            primary_reason=opp.primary_reason,
            confidence=opp.confidence,
            impressions_90d=met.impressions_90d if met else 0.0,
            clicks_90d=met.clicks_90d if met else 0.0,
            ctr=met.ctr if met else 0.0,
            avg_position=met.avg_position if met else 0.0,
            days_since_last_update=pg.days_since_last_update,
            content_type=pg.content_type,
            main_intent=pg.main_intent,
            domain=pg.domain,
            url=pg.url,
            page_title=pg.page_title,
            page_type=pg.page_type,
            page_type_source=pg.page_type_source,
        ))

    total_pages = max(1, (total + limit - 1) // limit)
    return PaginatedOpportunities(
        total=total,
        page=page,
        page_size=limit,
        total_pages=total_pages,
        items=items,
    )


@router.delete("/{dataset_id}")
def delete_dataset(
    dataset_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """
    Deletes a user-uploaded dataset and its associated pages, metrics, and opportunities.
    Prevents deletion of the permanent FlyRank Starter Dataset.
    """
    ds = db.query(Dataset).filter(Dataset.dataset_id == dataset_id).first()
    if not ds:
        raise HTTPException(status_code=404, detail=f"Dataset '{dataset_id}' not found.")

    if ds.is_starter or dataset_id == "starter-flyrank":
        raise HTTPException(
            status_code=400,
            detail="Deletion Forbidden: The bundled FlyRank Starter/Demo Dataset cannot be deleted or archived.",
        )

    db.query(Opportunity).filter(Opportunity.dataset_id == dataset_id).delete(synchronize_session=False)
    db.query(Page).filter(Page.dataset_id == dataset_id).delete(synchronize_session=False)
    db.delete(ds)
    db.commit()

    csv_file = UPLOADS_DIR / f"{dataset_id}.csv"
    if csv_file.exists():
        try:
            csv_file.unlink()
        except OSError:
            pass

    archetype_file = BASE_DIR / "data" / "archetypes" / f"{dataset_id}.json"
    if archetype_file.exists():
        try:
            archetype_file.unlink()
        except OSError:
            pass

    return {
        "status": "deleted",
        "dataset_id": dataset_id,
        "message": f"Dataset '{ds.name}' and all associated records have been removed successfully.",
    }
