import { ChevronRight } from "lucide-react";
import { type FormEvent, type ReactNode, useState } from "react";
import { api } from "@/api/client";
import { Button } from "@/components/ui/button";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import {
  defaultFileSettings,
  FileSection,
  type FileSettings,
  generationRequest,
} from "@/workbench/generate/FileSection";
import type { Generation } from "@/workbench/generate/useGeneration";

function Section({ title, hint, children }: { title: string; hint: string; children: ReactNode }) {
  return (
    <Collapsible className="group rounded-xl border bg-card">
      <div className="flex items-center gap-3 px-5 py-4">
        <CollapsibleTrigger className="flex flex-1 items-center gap-3 text-left">
          <ChevronRight
            className="size-4 shrink-0 transition-transform group-data-[state=open]:rotate-90"
            aria-hidden
          />
          <span className="font-medium text-base">{title}</span>
        </CollapsibleTrigger>
        <span className="text-muted-foreground text-sm">{hint}</span>
      </div>
      <CollapsibleContent className="space-y-6 px-5 pt-1 pb-6">{children}</CollapsibleContent>
    </Collapsible>
  );
}

/** File, Data and Hits sections, collapsed until needed, with the Generate button always in reach (spec 13.2). */
export function SettingsPane({ generation }: { generation: Generation }) {
  const options = api.useQuery("get", "/api/v1/options");
  const messageVersions = api.useQuery("get", "/api/v1/message-versions");
  // Only what the user changed; everything else follows the API's defaults once they load.
  const [changed, setChanged] = useState<Partial<FileSettings>>({});
  const settings = options.data === undefined ? undefined : { ...defaultFileSettings(options.data), ...changed };

  const onSubmit = (event: FormEvent) => {
    event.preventDefault();
    if (settings !== undefined) {
      generation.generate(generationRequest(changed));
    }
  };

  return (
    <form className="flex flex-col gap-4" onSubmit={onSubmit}>
      <div className="px-1 pb-2">
        <h1 className="font-semibold text-xl tracking-tight">pain.001 Sample File generator</h1>
        <p className="mt-1 text-muted-foreground text-sm">
          Generate a Sample File and the Answer Key that goes with it.
        </p>
      </div>
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
        <p className="text-muted-foreground text-sm">Hits arrive with the Entity Catalogue.</p>
      </Section>
      <div className="sticky bottom-6 mt-2">
        <Button type="submit" size="lg" className="w-full" disabled={settings === undefined || generation.isPending}>
          {generation.isPending ? "Generating…" : "Generate"}
        </Button>
      </div>
    </form>
  );
}
