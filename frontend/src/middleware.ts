import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";

// Public routes accessible without signing in
const isPublicRoute = createRouteMatcher([
  "/",
  "/auth(.*)",
  "/api(.*)",
  "/favicon.ico",
]);

export default clerkMiddleware((auth, req) => {
  // Gracefully skip route protection during build or when key is placeholder
  const pubKey = process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY;
  if (!pubKey || pubKey.includes("placeholder")) {
    return;
  }

  if (!isPublicRoute(req)) {
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
