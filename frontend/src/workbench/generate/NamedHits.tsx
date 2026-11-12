import type { components } from "@/api/schema";
import { Button } from "@/components/ui/button";
import { Chips, Field, INPUT, LABEL, toggle } from "@/workbench/generate/FileSection";

type Options = components["schemas"]["Options"];
type Entity = components["schemas"]["EntitySummary"];
type EntityType = components["schemas"]["EntityType"];
type Placement = components["schemas"]["Placement"];
type NameVariant = components["schemas"]["NameVariant"];
type RenderingMode = components["schemas"]["RenderingMode"];
type NamedHit = components["schemas"]["NamedHit"];
type FieldError = components["schemas"]["FieldError"];

/** One row of the Hits section; an empty string is "drawn". */
export type NamedHitRow = {
  key: number;
  entity: string;
  placement: Placement | "";
  name_variant: NameVariant | "";
  transaction: string;
  rendering_mode: RenderingMode | "";
  with_controller: boolean;
};

export type HitSettings = { rows: NamedHitRow[]; placements: Placement[]; name_variants: NameVariant[] };

/** Only what each row pins; an empty row still goes, so the API's `hits[i]` errors line up with the rows. */
export function hitsRequest({ rows, placements, name_variants }: HitSettings) {
  return {
    ...(rows.length
      ? {
          hits: rows.map(
            (row): Partial<NamedHit> => ({
              entity: row.entity,
              ...(row.placement ? { placement: row.placement } : {}),
              ...(row.name_variant ? { name_variant: row.name_variant } : {}),
              ...(row.transaction ? { transaction: Number(row.transaction) } : {}),
              ...(row.rendering_mode ? { rendering_mode: row.rendering_mode } : {}),
              ...(row.with_controller ? { with_controller: true } : {}),
            }),
            // Every field but the Entity is optional on the wire; the generated type marks those with defaults required.
          ) as NamedHit[],
        }
      : {}),
    ...(placements.length ? { placements } : {}),
    ...(name_variants.length ? { name_variants } : {}),
  };
}

const ENTITY_GROUPS: [EntityType, string][] = [
  ["bank", "Banks"],
  ["corporate", "Corporates"],
  ["individual", "Individuals"],
];

function placementLabel(placement: Placement) {
  return placement
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

let nextKey = 0;

/** Named Hit rows and the allowlists for the drawn ones (spec 13.2); `errors` are the 422's, shown on their rows. */
export function NamedHits({
  options,
  entities,
  transactionCount,
  value,
  onChange,
  errors,
}: {
  options: Options;
  entities: Entity[];
  transactionCount: string;
  value: HitSettings;
  onChange: (value: HitSettings) => void;
  errors: FieldError[];
}) {
  const setRow = (index: number, patch: Partial<NamedHitRow>) =>
    onChange({ ...value, rows: value.rows.map((row, i) => (i === index ? { ...row, ...patch } : row)) });
  const add = () =>
    onChange({
      ...value,
      rows: [
        ...value.rows,
        {
          key: nextKey++,
          entity: "",
          placement: "",
          name_variant: "",
          transaction: "",
          rendering_mode: "",
          with_controller: false,
        },
      ],
    });

  return (
    <>
      {value.rows.map((row, index) => {
        const entity = entities.find((e) => e.id === row.entity);
        const placement = options.placements.find((p) => p.placement === row.placement);
        const prefix = `hits[${index}]`;
        const rowErrors = errors.filter((e) => e.field === prefix || e.field.startsWith(`${prefix}.`));
        const invalid = (field: string) => rowErrors.some((e) => e.field === `${prefix}.${field}`);
        return (
          // biome-ignore lint/a11y/useSemanticElements: a labelled row of fields, styled as a card
          <div
            key={row.key}
            role="group"
            aria-label={`Named Hit ${index + 1}`}
            className="space-y-3 rounded-lg border p-4"
          >
            <div className="flex items-end gap-3">
              <div className="flex-1">
                <Field label="Entity">
                  <select
                    className={INPUT}
                    value={row.entity}
                    aria-invalid={invalid("entity")}
                    onChange={(e) =>
                      setRow(index, {
                        entity: e.target.value,
                        placement: "",
                        name_variant: "",
                        rendering_mode: "",
                        with_controller: false,
                      })
                    }
                  >
                    <option value="">Choose an Entity</option>
                    {ENTITY_GROUPS.map(([type, label]) => (
                      <optgroup key={type} label={label}>
                        {entities
                          .filter((e) => e.entity_type === type)
                          .map((e) => (
                            <option key={e.id} value={e.id}>
                              {e.display_name}
                            </option>
                          ))}
                      </optgroup>
                    ))}
                  </select>
                </Field>
              </div>
              <Button
                type="button"
                variant="outline"
                onClick={() => onChange({ ...value, rows: value.rows.filter((_, i) => i !== index) })}
              >
                Remove
              </Button>
            </div>
            <div className="grid grid-cols-3 gap-3">
              <Field label="Placement">
                <select
                  className={INPUT}
                  value={row.placement}
                  aria-invalid={invalid("placement")}
                  onChange={(e) => {
                    const chosen = options.placements.find((p) => p.placement === e.target.value);
                    setRow(index, {
                      placement: chosen?.placement ?? "",
                      ...(chosen?.file_level ? { transaction: "" } : {}),
                      ...(chosen && !chosen.agent ? { rendering_mode: "" } : {}),
                    });
                  }}
                >
                  <option value="">Drawn</option>
                  {options.placements.map((p) => (
                    <option
                      key={p.placement}
                      value={p.placement}
                      disabled={entity !== undefined && !entity.placements.includes(p.placement)}
                    >
                      {placementLabel(p.placement)}
                      {p.file_level ? " (file-level)" : ""}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="Name Variant">
                <select
                  className={INPUT}
                  value={row.name_variant}
                  aria-invalid={invalid("name_variant")}
                  onChange={(e) => setRow(index, { name_variant: e.target.value as NameVariant | "" })}
                >
                  <option value="">Drawn</option>
                  {options.name_variants.map((variant) => (
                    <option
                      key={variant}
                      value={variant}
                      disabled={entity !== undefined && !entity.name_variants.includes(variant)}
                    >
                      {variant}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="Transaction">
                <input
                  type="number"
                  className={INPUT}
                  min={1}
                  max={Number(transactionCount) || undefined}
                  placeholder="Drawn"
                  disabled={placement?.file_level}
                  value={row.transaction}
                  aria-invalid={invalid("transaction")}
                  onChange={(e) => setRow(index, { transaction: e.target.value })}
                />
              </Field>
            </div>
            {entity?.entity_type === "bank" && (placement === undefined || placement.agent) ? (
              <Field label="Rendering mode">
                <select
                  className={INPUT}
                  value={row.rendering_mode}
                  aria-invalid={invalid("rendering_mode")}
                  onChange={(e) => setRow(index, { rendering_mode: e.target.value as RenderingMode | "" })}
                >
                  <option value="">Default</option>
                  {options.rendering_modes.map((mode) => (
                    <option key={mode} value={mode} disabled={mode === "bic_only" && !entity.has_bic}>
                      {mode}
                    </option>
                  ))}
                </select>
              </Field>
            ) : null}
            {entity?.has_controller ? (
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={row.with_controller}
                  aria-invalid={invalid("with_controller")}
                  onChange={(e) => setRow(index, { with_controller: e.target.checked })}
                />
                Add controller as Ultimate party
              </label>
            ) : null}
            {rowErrors.map((e) => (
              <p key={`${e.field}:${e.message}`} className="text-destructive text-sm">
                {e.message}
              </p>
            ))}
          </div>
        );
      })}
      <Button type="button" variant="outline" onClick={add}>
        Add named Hit
      </Button>
      <div className="flex flex-col gap-2 text-xs">
        <span className={LABEL}>Drawn Placements</span>
        <Chips
          label="Drawn Placements"
          all={options.placements.map((p) => p.placement)}
          chosen={value.placements}
          onToggle={(p) => onChange({ ...value, placements: toggle(value.placements, p) })}
        />
        <span className={LABEL}>Drawn Name Variants</span>
        <Chips
          label="Drawn Name Variants"
          all={options.name_variants}
          chosen={value.name_variants}
          onToggle={(v) => onChange({ ...value, name_variants: toggle(value.name_variants, v) })}
        />
        <span className="text-muted-foreground">None chosen: the drawn Hits may take any.</span>
      </div>
    </>
  );
}
