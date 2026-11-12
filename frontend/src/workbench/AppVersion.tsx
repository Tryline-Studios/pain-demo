import { api } from "@/api/client";

/** The app version from `GET /api/v1/version`, a small label in the Workbench header. */
export function AppVersion() {
  const version = api.useQuery("get", "/api/v1/version");

  return (
    <p className="text-muted-foreground text-sm">
      Version{" "}
      {version.isPending ? (
        <span>…</span>
      ) : version.data === undefined ? (
        <span className="text-destructive">unavailable</span>
      ) : (
        <span title={`git ${version.data.git_sha}`}>{version.data.app_version}</span>
      )}
    </p>
  );
}
