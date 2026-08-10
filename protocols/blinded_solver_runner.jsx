import { useState } from "react";

// BLINDED SOLVER RUNNER — v44
// Each "model solve" is ONE fresh API call whose entire context is the single
// item below: no authoring history, no keys, no project documents
// (DIFFICULTY_EVIDENCE_RULINGS_V1 R9; operator instruction, blinded-review
// stage). The authoring agent produced no record here. Automated records are
// supplementary evidence only: a named human performs A5 acceptance and A7
// adjudication.

const ITEMS = [
 {
  "id": "AR_TAX_0001",
  "stimulus": "City transit planner: Ridership on the Elm Street bus line rose eleven percent in the six months after we widened the sidewalks along its route. Some colleagues credit the systemwide fare discount introduced around the same time. But that discount applied to every line in the network, while no other line gained riders at anything near that rate. The sidewalk project made walking to Elm Street stops easier, and that improved access is what drove the gain.",
  "stem": "Which one of the following, if true, most strengthens the planner's argument?",
  "choices": {
   "A": "After the sidewalks were widened, several regular Elm Street riders reported that they would have begun riding the line even without the improvements.",
   "B": "Boarding records show that nearly all of the additional Elm Street trips began at stops located within the blocks where sidewalks were widened, and few began elsewhere on the line.",
   "C": "Citywide surveys show that residents consider convenient access among the most important factors in choosing how to commute.",
   "D": "The eleven percent increase on Elm Street began in the very month that the sidewalk project was completed.",
   "E": "The Elm Street line now carries more riders than the Oak Avenue line, which serves a similar number of households."
  }
 },
 {
  "id": "AR_TAX_0002",
  "stimulus": "Ecologist: Streams in the Harlow watershed show mayfly counts forty percent below their ten-year average. Farm runoff is the usual suspect in such declines, and this watershed does border cropland. Yet the better explanation is last summer's channel-dredging project: mayfly larvae anchor in gravel beds, and the dredging stripped those beds from long stretches of the streams. It was the dredging, not runoff, that depressed the mayfly population.",
  "stem": "Which one of the following, if true, most strengthens the ecologist's argument?",
  "choices": {
   "A": "Mayfly counts in the Harlow watershed began falling within weeks of the start of the dredging project.",
   "B": "Streams in a neighboring watershed that were never dredged showed a similar decline in mayfly counts over the same period.",
   "C": "Insect populations of many kinds have declined across the region over the past decade.",
   "D": "Water sampled monthly throughout the decline showed agricultural chemical concentrations no higher than in years when mayfly counts were normal.",
   "E": "Mayflies are an important food source for several fish species native to the Harlow watershed."
  }
 },
 {
  "id": "AR_TAX_0003",
  "stimulus": "Every proposal that reaches the board has first been reviewed by the finance committee, and every proposal the finance committee reviews receives a written risk assessment. The Meridian proposal has never received a written risk assessment. It follows that the Meridian proposal has not reached the board.",
  "stem": "The pattern of reasoning in which one of the following arguments is most similar to that in the argument above?",
  "choices": {
   "A": "Every violin in the Deller collection was crafted before 1900, and every instrument crafted before 1900 requires climate-controlled storage. The Amati violin is in the Deller collection. Therefore, the Amati violin requires climate-controlled storage.",
   "B": "Every ferry that crosses the strait carries a licensed pilot. The Northwind is not carrying a licensed pilot, and it is not certified for open water either. Therefore, the Northwind is not crossing the strait.",
   "C": "Every entree on the tasting menu is prepared by the head chef, and every dish the head chef prepares is plated on the restaurant's signature stoneware. This soup is not plated on the signature stoneware. Therefore, this soup is not an entree on the tasting menu.",
   "D": "Every cottage on the ridge has a slate roof, and every building with a slate roof passed last year's fire inspection. The Hartley cottage passed last year's fire inspection. Therefore, the Hartley cottage is on the ridge.",
   "E": "Most of the orchids in the greenhouse are hybrids, and most hybrids tolerate cool nights. This orchid is from the greenhouse. Therefore, this orchid probably tolerates cool nights."
  }
 },
 {
  "id": "AR_TAX_0004",
  "stimulus": "Whenever the harbor mill runs its night shift, the water outflow near the pier turns noticeably warm by evening. On Tuesday the outflow near the pier was noticeably warm by evening. So the harbor mill must have been running its night shift on Tuesday evening as well.",
  "stem": "The flawed pattern of reasoning in the argument above is most similar to that in which one of the following?",
  "choices": {
   "A": "Whenever the express train is late, the platform display shows a delay notice, and the display never shows one in error. The display is showing a delay notice. So the express train is late.",
   "B": "Whenever the orchard's irrigation system runs, the reservoir level drops by morning. The irrigation system did not run last night. So the reservoir level will not have dropped by morning.",
   "C": "Whenever the print shop calibrates its press, the proof sheets come out aligned. Today's proof sheets did not come out aligned. So the print shop did not calibrate its press today.",
   "D": "The last three winters in Dorsey County have been unusually mild. So winters in Dorsey County are becoming permanently milder.",
   "E": "Whenever the bakery tests a new sourdough recipe, the whole block smells of fresh bread by midmorning. On Friday the block smelled of fresh bread by midmorning. So the bakery must have been testing a new sourdough recipe on Friday."
  }
 },
 {
  "id": "AR_TAX_0005",
  "stimulus": "Columnist: The city council should not have approved the riverfront tower. In a large randomized survey of city residents conducted last month, nearly eighty percent said the tower would harm the city's character. A decision opposed by so clear a majority of residents cannot have been the right one.",
  "stem": "The reasoning in the columnist's argument is most vulnerable to criticism on the grounds that the argument",
  "choices": {
   "A": "takes the fact that a view is widely held to establish that the view is correct",
   "B": "relies on a sample of residents that is unlikely to be representative of the city as a whole",
   "C": "presents as a premise a claim that merely restates the argument's conclusion",
   "D": "draws a conclusion about all future development projects from evidence concerning a single tower",
   "E": "criticizes the council's decision without identifying the individual council members responsible for it"
  }
 },
 {
  "id": "AR_TAX_0006",
  "stimulus": "Manager: Our cafe's loyalty-card program is working. In the six months since we introduced the cards, the average number of monthly visits per cardholder has been well above the average number of monthly visits per customer in the six months before the program began. Clearly, the cards are encouraging people to come in more often.",
  "stem": "Which one of the following, if true, most seriously weakens the manager's argument?",
  "choices": {
   "A": "Loyalty-card programs have failed to increase overall sales at most cafes that have tried them.",
   "B": "Several cardholders say that the promise of rewards is what first led them to visit the cafe more frequently.",
   "C": "A nearby cafe that introduced a loyalty program at the same time has seen an even larger increase in visits per cardholder.",
   "D": "The customers who signed up for loyalty cards were, even before the program began, visiting the cafe far more often than the average customer.",
   "E": "The cafe's loyalty cards are printed on recycled stock that costs slightly more than standard card material."
  }
 },
 {
  "id": "AR_TAX_0007",
  "stimulus": "Principal: Attendance at Brookside High improved markedly this fall, the first term since we moved the school's start time an hour later. The later start is what produced the improvement: students who once slept through first period are now arriving on time and staying for the full day.",
  "stem": "Which one of the following, if true, most seriously weakens the principal's argument?",
  "choices": {
   "A": "Improved attendance following a schedule change does not by itself establish that the change caused the improvement.",
   "B": "This fall the district began running a new express bus route that, for the first time, brings students from the far side of town directly to Brookside High.",
   "C": "Surveys show that most Brookside students feel more rested and more willing to attend school since the start time moved.",
   "D": "At schools in several other districts, later start times have failed to improve graduation rates.",
   "E": "Brookside High's attendance records are compiled by the same office that originally proposed the later start time."
  }
 },
 {
  "id": "AR_TAX_0008",
  "stimulus": "Grant officer: The Halloway Fund supports projects that are likely to expand public access to the performing arts. The Delta Theater's application proposes free weekend matinees in neighborhoods that have no permanent performance venue, and its budget is, by the Fund's usual standards, a modest one. So the Delta Theater's project is one the Halloway Fund is likely to support.",
  "stem": "The grant officer's argument depends on assuming which one of the following?",
  "choices": {
   "A": "The Halloway Fund supports every project that would expand public access to the performing arts while staying within a modest budget.",
   "B": "The Delta Theater has successfully staged free public performances in previous seasons.",
   "C": "If the Halloway Fund is likely to support a project, that project will expand public access to the performing arts.",
   "D": "It was the absence of performance venues in those neighborhoods that led the Delta Theater to propose weekend matinees there.",
   "E": "Free weekend matinees in neighborhoods without a permanent performance venue would be likely to expand public access to the performing arts."
  }
 },
 {
  "id": "AR_TAX_0009",
  "stimulus": "Agricultural bulletin: Most of the orchards in the Calder Valley, a region long known for its fruit exports, are certified organic. Every certified-organic orchard, whatever its size or output, is inspected annually by the agricultural board. And under the reporting regulation the province adopted this spring, no orchard that the board inspects annually is exempt from the new pesticide-reporting rule, regardless of what it grows.",
  "stem": "Which one of the following is most strongly supported by the statements above?",
  "choices": {
   "A": "Most of the orchards in the Calder Valley are not inspected annually by the agricultural board.",
   "B": "No orchard in the Calder Valley is exempt from the new pesticide-reporting rule.",
   "C": "Most of the orchards in the Calder Valley are not exempt from the new pesticide-reporting rule.",
   "D": "Most of the orchards that the agricultural board inspects annually are in the Calder Valley.",
   "E": "Any orchard that is not inspected annually by the agricultural board is not in the Calder Valley."
  }
 }
];

const MIN_COUNTS = { AR_TAX_0003: 5, AR_TAX_0004: 5 };
const minFor = (id) => MIN_COUNTS[id] || 3;
const MODEL = "claude-sonnet-4-6";

const SOLVER_PROMPT = (item) =>
  `You are solving one LSAT Logical Reasoning question. You have no other context and should use none.\n\n` +
  `${item.stimulus}\n\n${item.stem}\n\n` +
  ["A", "B", "C", "D", "E"].map((L) => `(${L}) ${item.choices[L]}`).join("\n") +
  `\n\nRespond with ONLY a JSON object (no markdown fences, no other text) with exactly these keys:\n` +
  `{"selected_answer":"A-E","confidence":"low|medium|high","perceived_difficulty":1-5,` +
  `"second_choice":"A-E","brief_reasoning":"max 60 words",` +
  `"alternate_answer_concern":"one sentence naming any OTHER choice you consider genuinely defensible, or null"}`;

async function solveOnce(item) {
  const t0 = Date.now();
  const resp = await fetch("https://api.anthropic.com/v1/messages", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      model: MODEL,
      max_tokens: 1000,
      messages: [{ role: "user", content: SOLVER_PROMPT(item) }],
    }),
  });
  const data = await resp.json();
  const text = (data.content || [])
    .filter((b) => b.type === "text")
    .map((b) => b.text)
    .join("\n");
  const clean = text.replace(/```json|```/g, "").trim();
  let rec;
  try {
    rec = JSON.parse(clean);
  } catch (e) {
    rec = { parse_error: true, raw: clean.slice(0, 400) };
  }
  return {
    ...rec,
    item_id: item.id,
    solver_type: "fresh_model_context",
    model: MODEL,
    duration_ms: Date.now() - t0,
    recorded_at: new Date().toISOString(),
  };
}

const emptyHuman = {
  solver_name: "",
  selected_answer: "",
  confidence: "",
  perceived_difficulty: "",
  second_choice: "",
  brief_reasoning: "",
  alternate_answer_concern: "",
  completion_time_seconds: "",
};

export default function BlindedSolverRunner() {
  const [records, setRecords] = useState({});
  const [busy, setBusy] = useState({});
  const [err, setErr] = useState("");
  const [humanForms, setHumanForms] = useState({});
  const [showExport, setShowExport] = useState(false);

  const add = (id, rec) =>
    setRecords((r) => ({ ...r, [id]: [...(r[id] || []), rec] }));

  const runModel = async (item, n) => {
    setBusy((b) => ({ ...b, [item.id]: true }));
    setErr("");
    try {
      for (let i = 0; i < n; i++) add(item.id, await solveOnce(item));
    } catch (e) {
      setErr(`${item.id}: ${e.message}`);
    }
    setBusy((b) => ({ ...b, [item.id]: false }));
  };

  const runAll = async () => {
    for (const item of ITEMS) {
      const have = (records[item.id] || []).length;
      const need = Math.max(0, minFor(item.id) - have);
      if (need > 0) await runModel(item, need);
    }
  };

  const submitHuman = (id) => {
    const f = humanForms[id] || emptyHuman;
    if (!f.selected_answer || !f.solver_name) return;
    add(id, {
      ...f,
      perceived_difficulty: Number(f.perceived_difficulty) || null,
      completion_time_seconds: Number(f.completion_time_seconds) || null,
      alternate_answer_concern: f.alternate_answer_concern || null,
      item_id: id,
      solver_type: "human",
      recorded_at: new Date().toISOString(),
    });
    setHumanForms((h) => ({ ...h, [id]: { ...emptyHuman } }));
  };

  const allRecords = ITEMS.flatMap((it) => records[it.id] || []);
  const exportBlob = JSON.stringify(
    {
      artifact: "blinded_solve_records",
      generated_at: new Date().toISOString(),
      model_for_model_records: MODEL,
      counts_required: Object.fromEntries(ITEMS.map((i) => [i.id, minFor(i.id)])),
      records: allRecords,
    },
    null,
    1
  );

  return (
    <div className="max-w-2xl mx-auto p-4 text-sm">
      <h1 className="text-lg font-bold mb-1">Blinded Solver Runner — AR_TAX items (v44)</h1>
      <p className="mb-3 text-gray-700">
        Every model solve is a fresh, single-item API context: no authoring
        history, no keys. Minimums: 3 records per item; 5 for items 0003 and
        0004. Human records can be added per item below. Export and paste the
        JSON back into the governor chat.
      </p>
      <div className="flex gap-2 mb-4">
        <button onClick={runAll} className="px-3 py-2 bg-blue-600 text-white rounded">
          Run all remaining model solves
        </button>
        <button onClick={() => setShowExport(!showExport)} className="px-3 py-2 bg-gray-800 text-white rounded">
          {showExport ? "Hide" : "Show"} export JSON ({allRecords.length} records)
        </button>
      </div>
      {err && <div className="mb-3 p-2 bg-red-100 text-red-800 rounded">{err}</div>}
      {showExport && (
        <textarea readOnly value={exportBlob} className="w-full h-56 border p-2 font-mono text-xs mb-4" onFocus={(e) => e.target.select()} />
      )}
      {ITEMS.map((item) => {
        const recs = records[item.id] || [];
        const f = humanForms[item.id] || emptyHuman;
        const setF = (k, v) => setHumanForms((h) => ({ ...h, [item.id]: { ...f, [k]: v } }));
        return (
          <div key={item.id} className="border rounded p-3 mb-4">
            <div className="flex justify-between items-center mb-2">
              <span className="font-bold">{item.id}</span>
              <span className="text-xs text-gray-600">{recs.length} / {minFor(item.id)} records</span>
            </div>
            <p className="mb-2">{item.stimulus}</p>
            <p className="font-medium mb-1">{item.stem}</p>
            {["A", "B", "C", "D", "E"].map((L) => (
              <p key={L} className="ml-2">({L}) {item.choices[L]}</p>
            ))}
            <button
              disabled={!!busy[item.id]}
              onClick={() => runModel(item, Math.max(1, minFor(item.id) - recs.length))}
              className="mt-2 px-3 py-1 bg-blue-500 text-white rounded disabled:opacity-50"
            >
              {busy[item.id] ? "Running…" : `Run ${Math.max(1, minFor(item.id) - recs.length)} model solve(s)`}
            </button>
            {recs.map((r, i) => (
              <div key={i} className="mt-2 p-2 bg-gray-50 rounded text-xs">
                <b>{r.solver_type === "human" ? `human: ${r.solver_name}` : "model"}</b>{" "}
                → {r.selected_answer || "?"} · conf {r.confidence || "?"} · perceived d
                {r.perceived_difficulty ?? "?"} · 2nd {r.second_choice || "?"}
                {r.duration_ms ? ` · ${(r.duration_ms / 1000).toFixed(1)}s` : ""}
                {r.completion_time_seconds ? ` · ${r.completion_time_seconds}s` : ""}
                {r.parse_error && <span className="text-red-700"> parse_error</span>}
                <div className="text-gray-700 mt-1">{r.brief_reasoning}</div>
                {r.alternate_answer_concern && (
                  <div className="text-amber-800 mt-1">concern: {String(r.alternate_answer_concern)}</div>
                )}
              </div>
            ))}
            <details className="mt-2">
              <summary className="cursor-pointer text-gray-700">Add human record</summary>
              <div className="grid grid-cols-2 gap-2 mt-2">
                <input placeholder="solver name" value={f.solver_name} onChange={(e) => setF("solver_name", e.target.value)} className="border p-1" />
                <input placeholder="answer A-E" value={f.selected_answer} onChange={(e) => setF("selected_answer", e.target.value.toUpperCase())} className="border p-1" />
                <input placeholder="confidence low/medium/high" value={f.confidence} onChange={(e) => setF("confidence", e.target.value)} className="border p-1" />
                <input placeholder="perceived difficulty 1-5" value={f.perceived_difficulty} onChange={(e) => setF("perceived_difficulty", e.target.value)} className="border p-1" />
                <input placeholder="second choice A-E" value={f.second_choice} onChange={(e) => setF("second_choice", e.target.value.toUpperCase())} className="border p-1" />
                <input placeholder="time (seconds)" value={f.completion_time_seconds} onChange={(e) => setF("completion_time_seconds", e.target.value)} className="border p-1" />
                <textarea placeholder="brief reasoning" value={f.brief_reasoning} onChange={(e) => setF("brief_reasoning", e.target.value)} className="border p-1 col-span-2" />
                <input placeholder="alternate-answer concern or blank" value={f.alternate_answer_concern} onChange={(e) => setF("alternate_answer_concern", e.target.value)} className="border p-1 col-span-2" />
                <button onClick={() => submitHuman(item.id)} className="px-3 py-1 bg-green-700 text-white rounded col-span-2">
                  Add human record
                </button>
              </div>
            </details>
          </div>
        );
      })}
    </div>
  );
}
