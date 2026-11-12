import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { saveFile } from "@/lib/saveFile";
import { AnswerKeyTable } from "@/workbench/generate/AnswerKeyTable";
import { HighlightedXml } from "@/workbench/generate/HighlightedXml";
import { type Generation, siblingFilename } from "@/workbench/generate/useGeneration";
import { ProblemBlock } from "@/workbench/ProblemBlock";
import { Tile } from "@/workbench/Tile";

function Downloads({ generation }: { generation: Generation }) {
  const generated = generation.data;
  if (generated === undefined) {
    return null;
  }
  const { filename, xml } = generated.sample_file;
  return (
    // biome-ignore lint/a11y/useSemanticElements: a labelled row of buttons, not a form fieldset
    <div role="group" aria-label="Downloads" className="flex flex-wrap items-center gap-3">
      <span className="text-muted-foreground text-sm">Download</span>
      <Button variant="outline" onClick={() => generation.downloadZip(generated)}>
        Zip
      </Button>
      <Button variant="outline" onClick={() => saveFile(new Blob([xml], { type: "application/xml" }), filename)}>
        XML
      </Button>
      <Button
        variant="outline"
        onClick={() =>
          saveFile(
            new Blob([`${JSON.stringify(generated.answer_key, null, 2)}\n`], { type: "application/json" }),
            siblingFilename(filename, ".answer-key.json"),
          )
        }
      >
        Answer Key JSON
      </Button>
    </div>
  );
}

type OnValidate = (file: File) => void;

function Result({ generation, onValidate }: { generation: Generation; onValidate: OnValidate }) {
  const generated = generation.data;
  if (generated === undefined) {
    return null;
  }
  const { warnings } = generated.answer_key;
  return (
    <>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Downloads generation={generation} />
        <Button
          onClick={() =>
            onValidate(
              new File([generated.sample_file.xml], generated.sample_file.filename, { type: "application/xml" }),
            )
          }
        >
          Validate this Sample File
        </Button>
      </div>
      {generation.zipError === null ? null : <ProblemBlock error={generation.zipError} />}
      <Tabs defaultValue="answer-key">
        <TabsList>
          <TabsTrigger value="answer-key">Answer Key</TabsTrigger>
          <TabsTrigger value="xml">XML</TabsTrigger>
          <TabsTrigger value="warnings">Warnings ({warnings.length})</TabsTrigger>
        </TabsList>
        <TabsContent value="answer-key">
          <AnswerKeyTable hits={generated.answer_key.hits} />
        </TabsContent>
        <TabsContent value="xml">
          <HighlightedXml xml={generated.sample_file.xml} hits={generated.answer_key.hits} />
        </TabsContent>
        <TabsContent value="warnings">
          {warnings.length === 0 ? (
            <p className="text-muted-foreground text-sm">No warnings: the Message Version carried everything.</p>
          ) : (
            <ul className="list-disc space-y-1 pl-5 font-mono text-xs">
              {warnings.map((warning) => (
                <li key={warning}>{warning}</li>
              ))}
            </ul>
          )}
        </TabsContent>
      </Tabs>
    </>
  );
}

/** Summary tiles above the results; before the first generate, the empty state (spec 13.3). */
export function OutputPane({ generation, onValidate }: { generation: Generation; onValidate: OnValidate }) {
  const generated = generation.data;
  const file = generated?.answer_key.file;

  return (
    <div className="flex flex-col gap-6">
      <div className="grid grid-cols-2 gap-4 xl:grid-cols-4">
        <Tile label="Transactions">{file?.transaction_count ?? "–"}</Tile>
        <Tile label="Hits">{file?.hit_count ?? "–"}</Tile>
        <Tile label="Seed">
          <span className="block truncate" title={generated?.answer_key.seed}>
            {generated?.answer_key.seed ?? "–"}
          </span>
        </Tile>
        <Tile label="Version">
          <span className="block truncate">{generated?.answer_key.message_version ?? "–"}</span>
        </Tile>
      </div>
      {generation.error !== null ? (
        <ProblemBlock error={generation.error} />
      ) : generated !== undefined ? (
        <Result generation={generation} onValidate={onValidate} />
      ) : (
        <div className="flex min-h-[420px] flex-col items-center justify-center rounded-xl border border-dashed text-center">
          <p className="font-medium text-lg">{generation.isPending ? "Generating…" : "No Sample File yet"}</p>
          <p className="mt-2 max-w-md text-muted-foreground text-sm">
            Set up the file on the left and press Generate. The XML and any warnings will show here.
          </p>
        </div>
      )}
    </div>
  );
}
