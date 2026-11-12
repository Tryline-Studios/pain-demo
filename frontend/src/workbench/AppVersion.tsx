import { api } from "@/api/client";

/** The app version from `GET /api/v1/version`, a small label in the Workbench header. */
export function AppVersion() {
  const version = api.useQuery("get", "/api/v1/version");

  return (
    <p className="font-mono text-muted-foreground text-xs">
      {version.isPending ? (
        <span>v…</span>
      ) : version.data === undefined ? (
        <>
          version <span className="text-destructive">unavailable</span>
        </>
      ) : (
        <span title={`Version ${version.data.app_version}, git ${version.data.git_sha}`}>
          v<span>{version.data.app_version}</span>
        </span>
      )}
    </p>
  );
}
