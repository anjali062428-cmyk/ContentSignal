import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";

// Only authenticated application areas require sign-in
const isProtectedRoute = createRouteMatcher([
  "/dashboard(.*)",
]);

export default clerkMiddleware((auth, req) => {
  const pubKey = process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY;
  // If key is not configured or is a build placeholder, skip middleware enforcement
  if (!pubKey || pubKey.includes("placeholder")) {
    return;
  }

  // Only protect authenticated application areas (e.g. /dashboard/*)
  // Public pages (/, /auth, /architecture, /opportunities, /models, etc.) remain open
  if (isProtectedRoute(req)) {
    auth().protect();
  }
});

export const config = {
  matcher: [
    // Skip Next.js internals and all static files
    "/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",
    "/(api|trpc)(.*)",
  ],
};
