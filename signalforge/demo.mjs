import { DEFAULT_WEIGHTS } from "./core.mjs";
export function demoWorkspace() {
  const entities = [
    ["atlas", "Atlas Robotics", "Industrial automation"],
    ["northstar", "Northstar Energy", "Clean energy"],
    ["orbit", "Orbit Semiconductors", "Semiconductors"],
    ["meridian", "Meridian Logistics", "Supply chain"],
    ["lumen", "Lumen Health", "Healthcare technology"],
    ["verdant", "Verdant Materials", "Advanced materials"],
  ].map(([id, name, sector]) => ({ id, name, sector }));
  const specs = {
    atlas: [
      [
        "fit",
        2,
        "A manufacturing analytics pilot matches the current buying initiative.",
      ],
      ["growth", 2, "The fictional annual report describes 32% order growth."],
      [
        "timing",
        2,
        "A new production line is planned within the next quarter.",
      ],
      [
        "risk",
        1,
        "The sample balance sheet shows 24 months of operating cash.",
      ],
      [
        "timing",
        -1,
        "Procurement notes suggest the pilot budget may move to next year.",
      ],
    ],
    northstar: [
      ["fit", 2, "A grid modernization program requires asset monitoring."],
      ["growth", 1, "The sample backlog increased 18% year over year."],
      ["timing", 2, "The fictional RFP closes in six weeks."],
      ["risk", 1, "The sample program has a committed financing partner."],
    ],
    orbit: [
      [
        "fit",
        2,
        "Verification workflows match the proposed software offering.",
      ],
      ["growth", 2, "The sample design-services revenue grew 29%."],
      ["risk", -1, "One fictional customer represents 42% of revenue."],
    ],
    meridian: [
      [
        "fit",
        1,
        "Warehouse analytics aligns with a process improvement initiative.",
      ],
      ["growth", 0, "The sample shipment volume is flat year over year."],
      [
        "timing",
        1,
        "A fictional operations leader requested a discovery meeting.",
      ],
      ["risk", 1, "Sample contract renewals cover the next 18 months."],
    ],
    lumen: [
      ["fit", 1, "The sample data platform has an integration gap."],
      ["growth", 2, "The fictional provider network expanded by 35%."],
      ["timing", -1, "The sample security review delays new vendors."],
      [
        "risk",
        -2,
        "The fictional business has only nine months of cash runway.",
      ],
    ],
    verdant: [
      [
        "fit",
        1,
        "The sample plant digitization plan includes production reporting.",
      ],
      ["growth", 1, "The fictional company is adding a second facility."],
    ],
  };
  const evidence = entities.flatMap((e, i) =>
    specs[e.id].map(([factor, value, claim], j) => ({
      id: `${e.id}-${j}`,
      entityId: e.id,
      factor,
      value,
      claim,
      title: `Fictional ${["strategy memo", "annual report", "procurement note", "risk review", "follow-up memo"][j]} · ${e.name}`,
      url: "",
      date: new Date(Date.now() - (i * 8 + j * 13) * 86400000)
        .toISOString()
        .slice(0, 10),
      quality: j === 4 ? 2 : 3,
    })),
  );
  return {
    version: 1,
    title: "Industrial intelligence",
    demo: true,
    entities,
    evidence,
    weights: { ...DEFAULT_WEIGHTS },
    runs: [],
  };
}
