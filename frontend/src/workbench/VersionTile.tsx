import { api } from "@/api/client";
import { Tile } from "@/workbench/Tile";

/** The app version from `GET /api/v1/version`, the first thing the UI fetches through the generated client. */
export function VersionTile() {
  const version = api.useQuery("get", "/api/v1/version");

  return (
    <Tile label="Version">
      {version.isPending ? (
        <span className="text-muted-foreground">…</span>
      ) : version.data === undefined ? (
        <span className="text-destructive">unavailable</span>
      ) : (
        <span title={`git ${version.data.git_sha}`}>{version.data.app_version}</span>
      )}
    </Tile>
  );
}
