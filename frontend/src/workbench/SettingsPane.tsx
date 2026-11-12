import { ChevronRight } from "lucide-react";
import { type FormEvent, type ReactNode, useState } from "react";
import { api } from "@/api/client";
import type { components } from "@/api/schema";
import { Button } from "@/components/ui/button";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import {
  defaultFileSettings,
  Field,
  FileSection,
  type FileSettings,
  generationRequest,
  INPUT,
} from "@/workbench/generate/FileSection";
import { type HitSettings, hitsRequest, NamedHits } from "@/workbench/generate/NamedHits";
import type { Generation } from "@/workbench/generate/useGeneration";
import { PRIMARY_BUTTON } from "@/workbench/OutputPane";

function Section({ title, hint, children }: { title: string; hint: string; children: ReactNode }) {
  return (
    <Collapsible className="group border-b pb-5 last-of-type:border-b-0">
      <div className="flex items-center gap-3">
        <CollapsibleTrigger className="flex flex-1 items-center gap-2 rounded-sm text-left focus-visible:outline-2 focus-visible:outline-ring focus-visible:outline-offset-2">
          <ChevronRight
            className="size-3.5 shrink-0 text-muted-foreground transition-transform group-data-[state=open]:rotate-90"
            aria-hidden
          />
          <span className="font-semibold text-[11px] text-muted-foreground uppercase tracking-[0.08em]">{title}</span>
        </CollapsibleTrigger>
        <span className="text-muted-foreground text-xs">{hint}</span>
      </div>
      <CollapsibleContent className="space-y-5 pt-4">{children}</CollapsibleContent>
    </Collapsible>
  );
}

/** File, Data and Hits sections, collapsed until needed, with the Generate button always in reach (spec 13.2). */
export function SettingsPane({ generation }: { generation: Generation }) {
  const options = api.useQuery("get", "/api/v1/options");
  const messageVersions = api.useQuery("get", "/api/v1/message-versions");
  const entities = api.useQuery("get", "/api/v1/entities");
  const [hits, setHits] = useState<HitSettings>({ rows: [], placements: [], name_variants: [] });
  // A 422's field errors, so the named Hit rows can show theirs (spec 13.3).
  const fieldErrors =
    (generation.error as Partial<components["schemas"]["RequestValidationProblem"]> | null)?.errors ?? [];
  // Only what the user changed; everything else follows the API's defaults once they load.
  const [changed, setChanged] = useState<Partial<FileSettings>>({});
  const settings = options.data === undefined ? undefined : { ...defaultFileSettings(options.data), ...changed };
  // Undefined until the user touches it, so the API's default (no Hits) applies.
  const [hitCount, setHitCount] = useState<string>();
  // The API's limit (spec 12.4); an unreadable transaction count is left for the API to reject.
  const hitLimit = Number(settings?.transaction_count) + 2;
  const hitCountTooHigh = hitCount !== undefined && Number(hitCount) > hitLimit;

  const onSubmit = (event: FormEvent) => {
    event.preventDefault();
    if (settings !== undefined && !hitCountTooHigh) {
      generation.generate({
        ...generationRequest(changed),
        ...(hitCount === undefined ? {} : { hit_count: Number(hitCount) }),
        ...hitsRequest(hits),
      });
    }
  };

  return (
    <form className="flex flex-col gap-5" onSubmit={onSubmit}>
      <Section title="File" hint="Message Version, transactions, Seed">
        {settings === undefined || options.data === undefined || messageVersions.data === undefined ? (
          <p className="text-muted-foreground text-sm">
            {options.isError || messageVersions.isError ? "The options could not be loaded." : "Loading options…"}
          </p>
        ) : (
          <FileSection
            options={options.data}
            messageVersions={messageVersions.data}
            value={settings}
            onChange={(patch) => setChanged((previous) => ({ ...previous, ...patch }))}
          />
        )}
      </Section>
      <Section title="Data" hint="Generated or supplied">
        <p className="text-muted-foreground text-sm">Supplied Data arrives with its own tickets.</p>
      </Section>
      <Section title="Hits" hint="Hit Count and named Hits">
        <Field label="Hit Count">
          <input
            type="number"
            className={INPUT}
            min={0}
            max={Number.isFinite(hitLimit) ? hitLimit : undefined}
            value={hitCount ?? "0"}
            aria-invalid={hitCountTooHigh}
            onChange={(e) => setHitCount(e.target.value)}
          />
        </Field>
        {hitCountTooHigh ? (
          <p className="text-destructive text-sm">
            At most {hitLimit} Hits for {settings?.transaction_count} transactions.
          </p>
        ) : null}
        {options.data === undefined || settings === undefined ? null : (
          <NamedHits
            options={options.data}
            entities={entities.data ?? []}
            transactionCount={settings.transaction_count}
            value={hits}
            onChange={setHits}
            errors={fieldErrors}
          />
        )}
      </Section>
      <div className="sticky bottom-6">
        <Button
          type="submit"
          size="lg"
          className={`${PRIMARY_BUTTON} w-full`}
          disabled={settings === undefined || hitCountTooHigh || generation.isPending}
        >
          {generation.isPending ? "Generating…" : "Generate"}
        </Button>
      </div>
    </form>
  );
}
