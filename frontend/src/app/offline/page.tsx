export default function OfflinePage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-6">
      <div className="text-center">
        <h1 className="text-2xl font-semibold text-foreground">
          You&apos;re offline
        </h1>
        <p className="mt-2 text-muted-foreground">
          Please check your internet connection and try again.
        </p>
      </div>
    </div>
  );
}
