---
{ "id": "PY.M03.A", "module": "PY.M03", "title": "PY.M03 module assessment: data structures and strings", "minutes": 20 }
---
Answer without the lessons open and without AI. Work each answer out on paper **before** you type it; only your **first** answer counts. These are new variants, not the lesson quizzes. If you miss more than one, ask the mentor for practice on that topic before PY.M04.

```quiz
{ "id": "a1", "type": "output",
  "prompt": "What does this print?",
  "code": "log = [\"a\", \"b\", \"c\", \"d\"]\nprint(log[2:10], log[-10:-2], log[4:])\nprint(log[::-1][:2])",
  "answer": "['c', 'd'] ['a', 'b'] []\n['d', 'c']", "accept": ["['c','d'] ['a','b'] []\n['d','c']"],
  "explanation": "Slice bounds clamp into 0..len: 2:10 becomes 2:4, and -10:-2 becomes 0:2. 4: on a 4-item list is empty. [::-1] is a reversed copy, and [:2] takes its first two items." }
```

```quiz
{ "id": "a2", "type": "output",
  "prompt": "What does this print?",
  "code": "line = \"id,,name ,\"\nprint(line.split(\",\"))\nprint(len(\" a  b \".split(\" \")), len(\" a  b \".split()))",
  "answer": "['id', '', 'name ', '']\n5 2", "accept": ["['id','','name ','']\n5 2"],
  "explanation": "With a separator, every comma is a cut: ,, gives an empty field, the trailing comma gives one at the end, and spaces are kept. \" a  b \".split(\" \") is ['', 'a', '', 'b', ''] (5 items). split() with no argument collapses whitespace: ['a', 'b']." }
```

```quiz
{ "id": "a3", "type": "output",
  "prompt": "Top 3 endpoints by hits, ties alphabetical. What does this print?",
  "code": "stats = {\"/users\": 40, \"/login\": 75, \"/health\": 40, \"/orders\": 12}\ntop = sorted(stats.items(), key=lambda kv: (-kv[1], kv[0]))[:3]\nfor path, hits in top:\n    print(path, hits)",
  "answer": "/login 75\n/health 40\n/users 40",
  "explanation": "The key is (-hits, path): -75 sorts first, then the two -40 entries in alphabetical order (/health before /users). /orders is cut off by [:3]. The dict's insertion order plays no part." }
```

```quiz
{ "id": "a4", "type": "output",
  "prompt": "What does this print?",
  "code": "from collections import Counter\nc = Counter(\"mississippi\")\nprint(c.most_common(2))\nprint(c[\"z\"])",
  "answer": "[('i', 4), ('s', 4)]\n0", "accept": ["[('i',4),('s',4)]\n0"],
  "explanation": "'i' and 's' both occur 4 times. most_common breaks ties by first appearance, and 'i' (position 1) comes before 's' (position 2). That it's also alphabetical here is a coincidence. A Counter returns 0 for a missing key." }
```

```quiz
{ "id": "a5", "type": "output",
  "prompt": "What does this print?",
  "code": "a = [[1], [2]]\nb = a[:]\nb[0].append(9)\nb[1] = [7]\na[2:] = [[3]]\nprint(a)",
  "answer": "[[1, 9], [2], [3]]", "accept": ["[[1,9],[2],[3]]"],
  "explanation": "b is a new outer list holding the same inner lists (a shallow copy). b[0].append(9) mutates the inner list that a shares. b[1] = [7] only rebinds a slot in b. a[2:] is the empty slot at the end of a, so assigning to it appends [3]." }
```

```quiz
{ "id": "a6", "type": "output",
  "prompt": "What does this print?",
  "code": "words = [\"Go\", \"py\", \"GO\", \"rust\"]\nprint(sorted({w.lower() for w in words}))\ngen = (len(w) for w in words)\nprint(max(gen), sum(gen))",
  "answer": "['go', 'py', 'rust']\n4 0", "accept": ["['go','py','rust']\n4 0"],
  "explanation": "The set comprehension lowercases, so \"Go\" and \"GO\" become one item; sorted turns the set into a list. max consumes the whole generator (the longest word has 4 letters), so sum gets an exhausted generator and returns 0." }
```
