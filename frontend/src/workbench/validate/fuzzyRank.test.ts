import { describe, expect, it } from "vitest";
import { rank } from "@/workbench/validate/fuzzyRank";

const ROOT = "/Document/CstmrCdtTrfInitn";
const paths = [
  "/Document",
  ROOT,
  `${ROOT}/GrpHdr`,
  `${ROOT}/GrpHdr/MsgId`,
  `${ROOT}/GrpHdr/InitgPty/Nm`,
  `${ROOT}/PmtInf`,
  `${ROOT}/PmtInf/PmtInfId`,
  `${ROOT}/PmtInf/CdtTrfTxInf`,
  `${ROOT}/PmtInf/CdtTrfTxInf/PmtId/InstrId`,
  `${ROOT}/PmtInf/CdtTrfTxInf/Amt`,
  `${ROOT}/PmtInf/CdtTrfTxInf/Amt/InstdAmt`,
  `${ROOT}/PmtInf/CdtTrfTxInf/InstrForCdtrAgt/InstrInf`,
];

describe("fuzzy rank", () => {
  it("ranks the path whose segments match runs of the typed text first", () => {
    expect(rank("instamt", paths)[0]).toBe(`${ROOT}/PmtInf/CdtTrfTxInf/Amt/InstdAmt`);
  });

  it("ranks the shortest path first for a typed prefix", () => {
    expect(rank(`${ROOT}/Grp`, paths).slice(0, 2)).toEqual([`${ROOT}/GrpHdr`, `${ROOT}/GrpHdr/MsgId`]);
  });

  it("matches without regard to case", () => {
    expect(rank("MSGID", paths)).toEqual([`${ROOT}/GrpHdr/MsgId`]);
  });

  it("gives a tie to the shorter candidate", () => {
    expect(rank("ab", ["/x/ab/c", "/x/ab"])).toEqual(["/x/ab", "/x/ab/c"]);
  });

  it("drops candidates that do not contain the typed text as a subsequence", () => {
    expect(rank("zz", paths)).toEqual([]);
  });

  it("returns at most eight candidates", () => {
    expect(rank("d", paths)).toHaveLength(8);
    expect(rank("d", paths, 3)).toHaveLength(3);
  });
});
