import { Check, Download } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { saveFile } from "@/lib/saveFile";
import { AnswerKeyTable } from "@/workbench/generate/AnswerKeyTable";
import { HighlightedXml } from "@/workbench/generate/HighlightedXml";
import { type Generation, siblingFilename } from "@/workbench/generate/useGeneration";
import { ProblemBlock } from "@/workbench/ProblemBlock";
import { MonoValue, TILES, Tile } from "@/workbench/Tile";

/**
 * Buttons at the canvas's 36px height with a 6px radius, focused by the solid 2px outline the other controls use
 * (shadcn's faint ring is under 3:1 in Light).
 */
export const BUTTON =
  "h-9 rounded-md px-3.5 focus-visible:outline-solid focus-visible:outline-2 focus-visible:outline-ring focus-visible:outline-offset-1 focus-visible:ring-0";
/** The canvas's darker accent on hover keeps the label at 4.5:1 (shadcn's 80% primary does not). */
export const PRIMARY_BUTTON = `${BUTTON} hover:bg-primary-hover`;

type OnValidate = (file: File) => void;

/** The file name, the downloads and the way into Validate mode, above the tiles once a Sample File exists. */
function Header({ generation, onValidate }: { generation: Generation; onValidate: OnValidate }) {
  const generated = generation.data;
  if (generated === undefined) {
    return null;
  }
  const { filename, xml } = generated.sample_file;
  return (
    <div className="flex flex-wrap items-end justify-between gap-4">
      <div className="flex min-w-0 flex-col gap-1">
        <h2 className="font-semibold text-[22px] tracking-[-0.015em]">Sample File</h2>
        <span className="truncate font-mono text-label text-xs">{filename}</span>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        {/* biome-ignore lint/a11y/useSemanticElements: a labelled row of buttons, not a form fieldset */}
        <div role="group" aria-label="Downloads" className="flex flex-wrap items-center gap-2">
          <Button variant="outline" className={BUTTON} onClick={() => generation.downloadZip(generated)}>
            <Download aria-hidden />
            Zip
          </Button>
          <Button
            variant="outline"
            className={BUTTON}
            onClick={() => saveFile(new Blob([xml], { type: "application/xml" }), filename)}
          >
            <Download aria-hidden />
            XML
          </Button>
          <Button
            variant="outline"
            className={BUTTON}
            onClick={() =>
              saveFile(
                new Blob([`${JSON.stringify(generated.answer_key, null, 2)}\n`], { type: "application/json" }),
                siblingFilename(filename, ".answer-key.json"),
              )
            }
          >
            <Download aria-hidden />
            Answer Key JSON
          </Button>
        </div>
        <Button
          className={PRIMARY_BUTTON}
          onClick={() => onValidate(new File([xml], filename, { type: "application/xml" }))}
        >
          Validate this Sample File
        </Button>
      </div>
    </div>
  );
}

/** A line-variant tab: the accent underline sits on the tab list's bottom border. */
const TAB = "h-full flex-none px-0.5 text-label after:bottom-[-1px]! after:bg-primary! data-active:text-foreground";

function Result({ generation }: { generation: Generation }) {
  const generated = generation.data;
  if (generated === undefined) {
    return null;
  }
  const { warnings, hits } = generated.answer_key;
  return (
    <Tabs defaultValue="answer-key" className="min-w-0 gap-0 rounded-[10px] border bg-card shadow-xs">
      <TabsList variant="line" className="h-[42px]! w-full justify-start gap-5 border-b px-[18px]">
        <TabsTrigger value="answer-key" className={TAB}>
          Answer Key
        </TabsTrigger>
        <TabsTrigger value="xml" className={TAB}>
          XML
        </TabsTrigger>
        <TabsTrigger value="warnings" className={TAB}>
          Warnings ({warnings.length})
        </TabsTrigger>
      </TabsList>
      <TabsContent value="answer-key" className="min-w-0">
        <AnswerKeyTable hits={hits} />
      </TabsContent>
      <TabsContent value="xml" className="min-w-0">
        <HighlightedXml xml={generated.sample_file.xml} hits={hits} />
      </TabsContent>
      <TabsContent value="warnings" className="p-[18px]">
        {warnings.length === 0 ? (
          <p className="text-muted-foreground">No warnings: the Message Version carried everything.</p>
        ) : (
          <ul className="list-disc space-y-1 pl-5 font-mono text-xs">
            {warnings.map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
        )}
      </TabsContent>
    </Tabs>
  );
}

/** The file header, summary tiles and results; before the first generate, the empty state (spec 13.3). */
export function OutputPane({ generation, onValidate }: { generation: Generation; onValidate: OnValidate }) {
  const generated = generation.data;
  const file = generated?.answer_key.file;
  const hits = generated?.answer_key.hits ?? [];
  const remittance = hits.filter((hit) => hit.placement === "remittance").length;

  return (
    <div className="flex flex-col gap-6">
      <Header generation={generation} onValidate={onValidate} />
      {generation.zipError === null ? null : <ProblemBlock error={generation.zipError} />}
      <div className={TILES}>
        <Tile label="Transactions">{file?.transaction_count ?? "–"}</Tile>
        <Tile label="Hits">
          {file?.hit_count ?? "–"}
          {generated === undefined ? null : (
            <span className="font-normal text-muted-foreground text-xs tracking-normal">
              {hits.length - remittance} party · {remittance} remittance
            </span>
          )}
        </Tile>
        <Tile label="Message Version">
          <MonoValue>{generated?.answer_key.message_version ?? "–"}</MonoValue>
        </Tile>
        <Tile label="Seed">
          <MonoValue title={generated?.answer_key.seed}>{generated?.answer_key.seed ?? "–"}</MonoValue>
        </Tile>
        <Tile label="XSD">
          {/* The API refuses a Sample File that fails its XSD (a 500 build_failed), so one that arrived is valid. */}
          {generated === undefined ? (
            "–"
          ) : (
            <span className="flex items-center gap-2 text-base text-success">
              <Check className="size-[18px]" strokeWidth={2.4} aria-hidden />
              Valid
            </span>
          )}
        </Tile>
      </div>
      {generation.error !== null ? (
        <ProblemBlock error={generation.error} />
      ) : generated !== undefined ? (
        <Result generation={generation} />
      ) : (
        <div className="flex min-h-[420px] flex-col items-center justify-center rounded-[10px] border border-border-strong border-dashed bg-card px-4 text-center">
          <p className="font-semibold text-lg">{generation.isPending ? "Generating…" : "No Sample File yet"}</p>
          <p className="mt-2 max-w-md text-muted-foreground text-sm">
            Set up the file on the left and press Generate. The XML and any warnings will show here.
          </p>
        </div>
      )}
    </div>
  );
}
