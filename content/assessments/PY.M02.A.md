---
{ "id": "PY.M02.A", "module": "PY.M02", "title": "PY.M02 module assessment: names, objects, mutability", "minutes": 20 }
---
Answer without the lessons open and without AI. Only your **first** answer counts. Before each output question, sketch the labels and objects on paper: that is the skill being tested. The module goal is at least 4 of the 5 output questions right, plus a correct diagram in the last one. If you miss more, ask the mentor for practice on that topic before PY.M03.

```quiz
{"id": "a1", "type": "output", "prompt": "What does this print?", "code": "row = [0, 0]\ngrid = [row, row]\ngrid[0][1] = 5\nrow = [9, 9]\nprint(grid, row)", "answer": "[[0, 5], [0, 5]] [9, 9]", "explanation": "grid holds two references to the one list that row pointed at. grid[0][1] = 5 mutates that list, so both slots show [0, 5]. row = [9, 9] then moves only the label row to a new list; grid still points at the old one."}
```

```quiz
{ "id": "a2", "type": "output",
  "prompt": "What does this print?",
  "code": "def process(batch, label):\n    batch += [\"done\"]\n    label += \"!\"\n    batch = [\"new\"]\n    batch.append(\"x\")\n    return label\n\njobs = [\"a\"]\nname = \"run\"\nout = process(jobs, name)\nprint(jobs, name, out)",
  "answer": "['a', 'done'] run run!",
  "explanation": "+= on a list extends the caller's list in place. += on a str builds a new string and rebinds only the local label, so name stays 'run' and the returned value is 'run!'. batch = [\"new\"] moves the local label, so the append after it never reaches jobs." }
```

```quiz
{ "id": "a3", "type": "output",
  "prompt": "What does this print?",
  "code": "import copy\nteam = {\"lead\": \"ali\", \"members\": [\"sara\", \"reza\"]}\nsnap1 = dict(team)\nsnap2 = copy.deepcopy(team)\nteam[\"lead\"] = \"sara\"\nteam[\"members\"].remove(\"reza\")\nprint(snap1)\nprint(snap2[\"members\"], snap1 is team)",
  "answer": "{'lead': 'ali', 'members': ['sara']}\n['sara', 'reza'] False",
  "explanation": "dict(team) is a shallow copy: a new dict (so snap1 is not team, and rebinding team['lead'] doesn't affect it) whose 'members' slot points at the same list, so the remove shows up. deepcopy copied the list too." }
```

```quiz
{"id": "a4", "type": "output", "prompt": "What does this print?", "code": "def opts(extra=[]):\n    return extra\n\na = opts()\na.append(\"v\")\nprint(opts(), a is opts())", "answer": "['v'] True", "explanation": "The default list is created once, when def runs, and opts() returns that same object every time. The caller's a.append mutates the stored default, so the next call returns ['v'], and it is the same object as a."}
```

```quiz
{"id": "a5", "type": "output", "prompt": "What does this print?", "code": "rows = [[1], [2]]\npart = rows[1:9]\npart[0].append(3)\npart.append([4])\nprint(rows, len(part), rows[5:])", "answer": "[[1], [2, 3]] 2 []", "explanation": "rows[1:9] clamps to the end and builds a new list holding the same inner list [2] (a slice is a shallow copy). part[0].append(3) goes through that shared inner list, so rows sees [2, 3]. part.append([4]) changes only the new outer list. rows[5:] clamps to an empty list instead of raising."}
```

```quiz
{ "id": "a6", "type": "explain", "label": "Diagram",
  "prompt": "A teammate says: \"Python passes lists by reference, so `def wipe(xs): xs = []` empties the caller's list.\" Draw the label → object diagram for `data = [1, 2]; wipe(data)` at the start and the end of the call, say what `data` is afterwards, and show two correct ways to write a function that really empties or replaces the caller's list.",
  "model": "At the call, data and xs are two labels on one list [1, 2]. xs = [] creates a new empty list and moves only xs to it; data still points at [1, 2], and the new list is dropped when wipe returns. So data is [1, 2]. Fix 1 (mutate): xs.clear() (or del xs[:]) empties the shared list. Fix 2 (return new): def wiped(xs): return [] and the caller writes data = wiped(data).",
  "explanation": "Python passes object references by assignment. Mutation through the parameter reaches the caller; rebinding the parameter never does." }
```
