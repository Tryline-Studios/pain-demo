import { Button } from "@/components/ui/button";
import { saveFile } from "@/lib/saveFile";
import { cn } from "@/lib/utils";
import { INPUT, LABEL } from "@/workbench/generate/FileSection";

/** Absent (generated from the Seed), explicit `null` (left out) or a value (spec 5.3). */
type TriState = "generate" | "omit" | "supply";

/** Text by dotted path into the Supplied Data (`creditor.address.country`); empty means generated. */
type Fields = Record<string, string>;

export type Row = { fields: Fields; modes: Record<string, TriState> };

/** Generated only, Supply some fields, or Upload CSV (spec 13.2); `csv` is the file chosen for the last. */
export type DataSettings = { mode: "generated" | "supply" | "csv"; payment: Fields; rows: Row[]; csv?: File };

export const defaultDataSettings: DataSettings = { mode: "generated", payment: {}, rows: [] };

type FieldSpec = { path: string; label: string };

const PAYMENT_FIELDS: FieldSpec[] = [
  { path: "debtor.name", label: "Debtor name" },
  { path: "debtor.address.country", label: "Debtor country" },
  { path: "debtor_account.iban", label: "Debtor IBAN" },
  { path: "debtor_agent.bic", label: "Debtor Agent BIC" },
  { path: "debtor_agent.name", label: "Debtor Agent name" },
];

const TRANSACTION_FIELDS: FieldSpec[] = [
  { path: "end_to_end_id", label: "End-to-end id" },
  { path: "creditor.name", label: "Creditor name" },
  { path: "creditor.address.country", label: "Creditor country" },
  { path: "creditor_account.iban", label: "Creditor IBAN" },
  { path: "creditor_agent.bic", label: "Creditor Agent BIC" },
  { path: "amount", label: "Amount" },
  { path: "currency", label: "Currency" },
  { path: "remittance.unstructured.0", label: "Remittance" },
];

/** Optional elements, each with the one field a Supply shows. */
const OPTIONAL_ELEMENTS: (FieldSpec & { field: FieldSpec })[] = [
  {
    path: "ultimate_debtor",
    label: "Ultimate Debtor",
    field: { path: "ultimate_debtor.name", label: "Ultimate Debtor name" },
  },
  {
    path: "ultimate_creditor",
    label: "Ultimate Creditor",
    field: { path: "ultimate_creditor.name", label: "Ultimate Creditor name" },
  },
  {
    path: "intermediary_agents",
    label: "Intermediary Agent",
    field: { path: "intermediary_agents.0.bic", label: "Intermediary Agent BIC" },
  },
  {
    path: "remittance.structured",
    label: "Structured remittance",
    field: { path: "remittance.structured.creditor_reference", label: "Creditor reference" },
  },
];

const TRI_STATES: [TriState, string][] = [
  ["generate", "Generate"],
  ["omit", "Leave out"],
  ["supply", "Supply"],
];

/** Sets `value` at a dotted path, making arrays for numeric segments: `remittance.unstructured.0`. */
function setPath(target: Record<string, unknown>, path: string, value: unknown) {
  const keys = path.split(".");
  let node: Record<string, unknown> = target;
  const last = keys.pop() as string;
  keys.forEach((key, index) => {
    node[key] ??= /^\d+$/.test(keys[index + 1] ?? last) ? [] : {};
    node = node[key] as Record<string, unknown>;
  });
  node[last] = value;
}

function nest(fields: Fields, modes: Record<string, TriState> = {}) {
  const body: Record<string, unknown> = {};
  const hidden = OPTIONAL_ELEMENTS.filter((e) => (modes[e.path] ?? "generate") !== "supply").map((e) => e.path);
  for (const [path, value] of Object.entries(fields)) {
    if (value !== "" && !hidden.some((element) => path.startsWith(`${element}.`))) setPath(body, path, value);
  }
  for (const [path, mode] of Object.entries(modes)) {
    if (mode === "omit") setPath(body, path, null);
  }
  return body;
}

/** `payment` and `transactions` for the request; nothing at all for Generated only. */
export function suppliedData(data: DataSettings) {
  if (data.mode !== "supply") return {};
  const payment = nest(data.payment);
  return {
    ...(Object.keys(payment).length ? { payment } : {}),
    ...(data.rows.length ? { transactions: data.rows.map((row) => nest(row.fields, row.modes)) } : {}),
  };
}

/** The API's dotted path for a field: `transactions[0].intermediary_agents[0].bic`. */
function apiPath(prefix: string, path: string) {
  return `${prefix}.${path.replace(/\.(\d+)/g, "[$1]")}`;
}

function TextField({
  spec,
  prefix,
  value,
  errors,
  onChange,
}: {
  spec: FieldSpec;
  prefix: string;
  value: string;
  errors: Map<string, string>;
  onChange: (value: string) => void;
}) {
  const path = apiPath(prefix, spec.path);
  const error = errors.get(path);
  const errorId = `${path}-error`;
  return (
    <div className="flex flex-col gap-1.5">
      <label className="flex flex-col gap-1.5">
        <span className={LABEL}>{spec.label}</span>
        <input
          type="text"
          className={INPUT}
          placeholder="Generated"
          value={value}
          aria-invalid={error !== undefined}
          aria-describedby={error === undefined ? undefined : errorId}
          onChange={(e) => onChange(e.target.value)}
        />
      </label>
      {error === undefined ? null : (
        <span id={errorId} className="text-destructive text-xs">
          {error}
        </span>
      )}
    </div>
  );
}

function TriStateControl({
  label,
  name,
  value,
  onChange,
}: {
  label: string;
  name: string;
  value: TriState;
  onChange: (value: TriState) => void;
}) {
  return (
    <div role="radiogroup" aria-label={label} className="flex flex-wrap items-center gap-3 text-sm">
      <span className={cn(LABEL, "min-w-36")}>{label}</span>
      {TRI_STATES.map(([state, text]) => (
        <label key={state} className="flex items-center gap-1.5">
          <input type="radio" name={name} checked={value === state} onChange={() => onChange(state)} />
          {text}
        </label>
      ))}
    </div>
  );
}

function ModeCard({
  checked,
  title,
  hint,
  onSelect,
}: {
  checked: boolean;
  title: string;
  hint: string;
  onSelect: () => void;
}) {
  return (
    <label
      className={cn("flex flex-1 cursor-pointer flex-col gap-1 rounded-lg border p-3 text-sm", {
        "border-primary bg-primary/5": checked,
      })}
    >
      <span className="flex items-center gap-2 font-medium">
        <input type="radio" name="data-mode" checked={checked} onChange={onSelect} />
        {title}
      </span>
      <span className="text-muted-foreground text-xs">{hint}</span>
    </label>
  );
}

/**
 * The Upload CSV card: the file, the flattened-field-path header it expects (spec 5.6) and that header as a template.
 * A 422 names `supplied_data[<row>].<column>` and shows in the problem block.
 */
function CsvUpload({ columns, onChange }: { columns: string[]; onChange: (csv: File | undefined) => void }) {
  const header = columns.join(",");
  return (
    <div className="flex flex-col gap-3">
      <label className="flex flex-col gap-1.5">
        <span className={LABEL}>Supplied Data CSV</span>
        <input type="file" accept=".csv,text/csv" className="text-sm" onChange={(e) => onChange(e.target.files?.[0])} />
      </label>
      <p className="text-muted-foreground text-xs">
        Columns are field paths. Payment columns are read from the first row; list positions count from 0 (
        <code>intermediary_agents.1.bic</code>). Leave out the columns you do not supply.
      </p>
      <code className="max-h-32 overflow-auto break-all rounded-md border bg-muted p-2 font-mono text-xs">
        {header}
      </code>
      <Button
        type="button"
        variant="outline"
        size="sm"
        className="self-start"
        onClick={() => saveFile(new Blob([`${header}\n`], { type: "text/csv" }), "supplied-data-template.csv")}
      >
        Download header template
      </Button>
    </div>
  );
}

/**
 * Generated only, or Supply some fields: payment-level fields once per file and per-transaction rows, each empty
 * field generated and each optional element Generate / Leave out / Supply (spec 13.2). A 422's dotted paths land on
 * the fields they name.
 */
export function DataSection({
  value,
  columns,
  errors,
  onChange,
}: {
  value: DataSettings;
  columns: string[];
  errors: Map<string, string>;
  onChange: (value: DataSettings) => void;
}) {
  const setRow = (index: number, row: Row) =>
    onChange({ ...value, rows: value.rows.map((r, i) => (i === index ? row : r)) });

  return (
    <>
      <div className="flex gap-3">
        <ModeCard
          checked={value.mode === "generated"}
          title="Generated only"
          hint="Every value drawn from the Seed"
          onSelect={() => onChange({ ...value, mode: "generated" })}
        />
        <ModeCard
          checked={value.mode === "supply"}
          title="Supply some fields"
          hint="Yours where given, the rest generated"
          onSelect={() => onChange({ ...value, mode: "supply" })}
        />
        <ModeCard
          checked={value.mode === "csv"}
          title="Upload CSV"
          hint="One row per transaction, empty cells generated"
          onSelect={() => onChange({ ...value, mode: "csv" })}
        />
      </div>
      {value.mode === "csv" ? <CsvUpload columns={columns} onChange={(csv) => onChange({ ...value, csv })} /> : null}
      {value.mode === "supply" ? (
        <>
          <fieldset className="flex flex-col gap-3">
            <legend className={cn(LABEL, "mb-2")}>Payment level (one per file)</legend>
            {PAYMENT_FIELDS.map((spec) => (
              <TextField
                key={spec.path}
                spec={spec}
                prefix="payment"
                value={value.payment[spec.path] ?? ""}
                errors={errors}
                onChange={(text) => onChange({ ...value, payment: { ...value.payment, [spec.path]: text } })}
              />
            ))}
          </fieldset>
          {value.rows.map((row, index) => {
            const prefix = `transactions[${index}]`;
            const setField = (path: string, text: string) =>
              setRow(index, { ...row, fields: { ...row.fields, [path]: text } });
            return (
              // biome-ignore lint/suspicious/noArrayIndexKey: rows are positional, as transaction numbers are
              <fieldset key={index} className="flex flex-col gap-3 rounded-lg border p-4">
                <legend className={cn(LABEL, "px-1")}>Transaction {index + 1}</legend>
                {TRANSACTION_FIELDS.map((spec) => (
                  <TextField
                    key={spec.path}
                    spec={spec}
                    prefix={prefix}
                    value={row.fields[spec.path] ?? ""}
                    errors={errors}
                    onChange={(text) => setField(spec.path, text)}
                  />
                ))}
                {OPTIONAL_ELEMENTS.map((element) => {
                  const mode = row.modes[element.path] ?? "generate";
                  return (
                    <div key={element.path} className="flex flex-col gap-2">
                      <TriStateControl
                        label={element.label}
                        name={`${prefix}.${element.path}`}
                        value={mode}
                        onChange={(next) => setRow(index, { ...row, modes: { ...row.modes, [element.path]: next } })}
                      />
                      {mode === "supply" ? (
                        <TextField
                          spec={element.field}
                          prefix={prefix}
                          value={row.fields[element.field.path] ?? ""}
                          errors={errors}
                          onChange={(text) => setField(element.field.path, text)}
                        />
                      ) : null}
                    </div>
                  );
                })}
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="self-start"
                  onClick={() => onChange({ ...value, rows: value.rows.filter((_, i) => i !== index) })}
                >
                  Remove transaction {index + 1}
                </Button>
              </fieldset>
            );
          })}
          <Button
            type="button"
            variant="outline"
            className="self-start"
            onClick={() => onChange({ ...value, rows: [...value.rows, { fields: {}, modes: {} }] })}
          >
            Add transaction
          </Button>
        </>
      ) : null}
    </>
  );
}
