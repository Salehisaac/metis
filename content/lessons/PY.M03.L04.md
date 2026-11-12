---
{
  "id": "PY.M03.L04",
  "title": "Strings: split, join, strip, f-strings",
  "difficulty": "beginner",
  "minutes": 50,
  "prerequisites": ["PY.M03.L03"],
  "objectives": [
    "Explain why string methods return new strings, and spot code that throws the result away",
    "Predict split() vs split(\" \") vs split(\",\") on inputs with repeated, leading and trailing separators, including the empty string",
    "Split only once with maxsplit when the value itself may contain the separator",
    "Use strip/lstrip/rstrip correctly (a set of characters, not a prefix) and removeprefix/removesuffix for real prefixes",
    "Build strings with join instead of += in a loop, and test text with in, startswith and endswith",
    "Format numbers and columns with f-string format specs: precision, width, alignment, fill, thousands separators, percent, ="
  ],
  "why": "Most backend input arrives as text: headers, query strings, CSV exports, config files, log lines. The split() vs split(\" \") difference and the empty fields from split(\",\") are exactly where your assessment answers went wrong, and they are also where real parsers silently produce wrong data.",
  "applications": [
    "Parsing headers, key=value config lines and CSV-like exports",
    "Normalising user input (emails, usernames) before storing or comparing it",
    "Routing or filtering by path prefix or file extension",
    "Formatting log lines, reports and CLI tables"
  ],
  "exercises": ["PY.M03.L04.E1"],
  "sources": [
    {
      "title": "Built-in Types: text sequence type (str methods) and common sequence operations",
      "url": "https://docs.python.org/3.12/library/stdtypes.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": [
        "split with sep: consecutive delimiters give empty strings; '1,,2'.split(',') is ['1', '', '2']; an empty string gives ['']",
        "split without sep: runs of whitespace are one separator, no empty strings at the ends; an empty or all-whitespace string gives []",
        "maxsplit limits the number of splits (at most maxsplit+1 items)",
        "strip/lstrip/rstrip: chars is not a prefix or suffix; all combinations of its values are stripped",
        "removeprefix/removesuffix remove one exact prefix/suffix",
        "join concatenates the strings of an iterable and raises TypeError for non-string items",
        "Repeated concatenation of immutable sequences has quadratic runtime cost; build a list and use str.join",
        "in tests for a substring; startswith/endswith accept a tuple of prefixes/suffixes"
      ]
    },
    {
      "title": "Python Tutorial: An Informal Introduction to Python (strings)",
      "url": "https://docs.python.org/3.12/tutorial/introduction.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": ["Strings are immutable; assigning to an indexed position raises TypeError"]
    },
    {
      "title": "Python Tutorial: Input and Output (formatted string literals)",
      "url": "https://docs.python.org/3.12/tutorial/inputoutput.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": [
        "f-strings: prefix f, expressions in {}, an optional format specifier after ':' such as .3f",
        "An integer after ':' sets a minimum field width",
        "!r applies repr(); the = specifier prints the expression text, '=' and the repr of the value"
      ]
    },
    {
      "title": "string: Format Specification Mini-Language",
      "url": "https://docs.python.org/3.12/library/string.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": [
        "Alignment < > ^ with an optional fill character before it; width is the minimum field width",
        "Precision with f gives that many digits after the decimal point",
        "',' inserts a thousands separator; '%' multiplies by 100 and adds a percent sign"
      ]
    }
  ]
}
---
## 1. Strings are immutable: methods return new strings

A Python `str` is an immutable sequence of characters, like a Go `string`. You can index and slice it (L01 rules apply), but you can't change it in place. Every method, such as `upper`, `replace` or `strip`, **returns a new string**:

```python
name = "metis"
name.upper()           # result thrown away
print(name)
name = name.upper()    # keep the result by rebinding the name
print(name)
name[0] = "X"
```

```console
metis
METIS
TypeError: 'str' object does not support item assignment
```

**Common mistake:** writing `email.strip()` or `email.lower()` on a line of its own and expecting `email` to change. Unlike `list.sort()`, string methods never change the original; you must use the return value.

```quiz
{ "id": "q1", "type": "output",
  "prompt": "What does this print?",
  "code": "s = \"go\"\ns.upper()\nt = s.replace(\"g\", \"G\")\nprint(s, t)",
  "answer": "go Go",
  "explanation": "s.upper() builds \"GO\" and throws it away; s still names \"go\". replace also returns a new string, which is kept in t." }
```

## 2. `split()` vs `split(" ")` vs `split(",")`

These are **two different algorithms** behind one method name. This is the gap from your assessment, so read the rule, not just the examples:

- **No argument:** split on **runs of whitespace** (spaces, tabs, newlines). Leading and trailing whitespace is ignored, so you never get empty strings.
- **With a separator:** split at **every single occurrence**. Two separators in a row, or one at either end, produce **empty strings**. Nothing is collapsed.

```python
line = "  GET   /users  200 "
print(line.split())
print(line.split(" "))
row = "ali,,tehran,"
print(row.split(","))
print("".split(","), "".split(), "   ".split())
```

```console
['GET', '/users', '200']
['', '', 'GET', '', '', '/users', '', '200', '']
['ali', '', 'tehran', '']
[''] [] []
```

That empty field is often *meaningful*. In CSV, `ali,,tehran` means "the second column is empty". If your code drops it, every later column shifts. But `split(" ")` on human-typed text is almost always a bug; you wanted `split()`. Go has the same pair: `strings.Fields` vs `strings.Split(s, " ")`.

Note the last line: `"".split(",")` is `['']`, a list with **one** empty string. So `len(text.split(","))` is never 0, even for empty input.

```quiz
{ "id": "q2", "type": "output",
  "prompt": "What does this print?",
  "code": "print(\"a  b \".split(\" \"))\nprint(\"a  b \".split())",
  "answer": "['a', '', 'b', '']\n['a', 'b']", "accept": ["['a','','b','']\n['a','b']"],
  "explanation": "With \" \" every single space is a cut: the double space leaves an empty string between a and b, and the trailing space leaves one at the end. With no argument, runs of whitespace count as one separator and the ends are ignored." }
```

```quiz
{ "id": "q3", "type": "output",
  "prompt": "What does this print?",
  "code": "print(len(\"\".split(\",\")), len(\"\".split()))",
  "answer": "1 0",
  "explanation": "With a separator, splitting \"\" gives [''] (one empty field). Without a separator, splitting \"\" gives []. Code that counts fields with split(\",\") must handle empty input separately." }
```

**Split once with `maxsplit`.** When the *value* may contain the separator, limit the number of splits:

```python
header = "Host: example.com:8080"
print(header.split(":"))
print(header.split(":", 1))
```

```console
['Host', ' example.com', '8080']
['Host', ' example.com:8080']
```

`split(":", 1)` cuts at the first colon only, so you always get at most 2 parts. Notice the leading space in `' example.com:8080'`: splitting doesn't trim. That's the next section.

```quiz
{ "id": "q4", "type": "output",
  "prompt": "What does this print?",
  "code": "print(\"x=1=2\".split(\"=\", 1))",
  "answer": "['x', '1=2']", "accept": ["['x','1=2']"],
  "explanation": "maxsplit=1 makes at most one cut, at the first '=', so the rest of the string stays together." }
```

## 3. `strip` removes characters, not a prefix

`strip()` with no argument removes leading and trailing **whitespace**. `lstrip()` does only the left and `rstrip()` only the right. With an argument, the docs warn that it is **a set of characters**, not a prefix or suffix: it keeps removing any of those characters from the end(s) until it hits one that isn't in the set.

```python
raw = "\t  admin@site.io \n"
print(repr(raw.strip()), repr(raw.lstrip()), repr(raw.rstrip()))
print("--v1--".strip("-"))
print("logs.csv".rstrip(".csv"))          # bug: eats the 's' of logs too
print("logs.csv".removesuffix(".csv"))   # removes the exact suffix once
```

```console
'admin@site.io' 'admin@site.io \n' '\t  admin@site.io'
v1
log
logs
```

Use `removeprefix` and `removesuffix` when you mean an exact prefix or suffix.

```quiz
{ "id": "q5", "type": "output", "label": "Debugging",
  "prompt": "Someone wants to drop the leading \"www.\" from a hostname. What does this print?",
  "code": "print(\"www.wiki.org\".lstrip(\"w.\"))\nprint(\"www.wiki.org\".removeprefix(\"www.\"))",
  "answer": "iki.org\nwiki.org",
  "explanation": "lstrip(\"w.\") removes every leading 'w' or '.', so it eats \"www.w\" and stops at 'i'. removeprefix removes exactly \"www.\" once." }
```

## 4. Build strings with `join`, test them with `in` and `startswith`

`sep.join(parts)` glues a list of strings together with `sep` in between. It's Go's `strings.Join`, except that the method belongs to the separator:

```python
parts = ["2026", "11", "12"]
print("-".join(parts))
print(", ".join(["go", "py"]))
", ".join([1, 2])
```

```console
2026-11-12
go, py
TypeError: sequence item 0: expected str instance, int found
```

- `join` accepts only strings. Convert numbers with `str()` first (L05 shows a one-line way).
- **`+=` in a loop vs `join`:** strings are immutable, so `out += piece` builds a new string every time. The docs warn that repeated concatenation can cost **quadratic** time in the total length, and recommend collecting the pieces in a list and calling `"".join(pieces)` once. It's the same idea as `strings.Builder` in Go. It also avoids the classic trailing-separator bug:

```quiz
{ "id": "q6", "type": "output",
  "prompt": "What does this print?",
  "code": "words = [\"to\", \"be\"]\nout = \"\"\nfor w in words:\n    out += w + \"/\"\nprint(out)\nprint(\"/\".join(words))",
  "answer": "to/be/\nto/be",
  "explanation": "The loop adds a separator after every word, including the last. join only puts the separator between items." }
```

To *test* text, use `in` (substring), `startswith` and `endswith`. Both of those accept a **tuple** of options:

```quiz
{ "id": "q7", "type": "output",
  "prompt": "What does this print?",
  "code": "path = \"/api/v1/users\"\nprint(\"v1\" in path, path.startswith((\"/admin\", \"/api\")), path.endswith(\"/\"))",
  "answer": "True True False",
  "explanation": "\"v1\" is a substring of the path. startswith with a tuple is true if any of the prefixes match (\"/api\" does). The path doesn't end with \"/\"." }
```

## 5. f-strings and format specs

An f-string evaluates the expressions in `{}`. After a `:` comes a **format spec**: `[fill]align width ,  .precision type`. It's the same idea as Go's `%-10s` and `%8.2f`, with different syntax:

```python
item, qty, price = "coffee", 3, 4.5
print(f"{item} x{qty} = {qty * price:.2f}")   # 2 digits after the point
print(f"{item:<10}|{qty:>4}|")                # left in 10, right in 4
print(f"{item:.<10}{price:>8.2f}")            # fill with dots
print(f"{1234567.891:,.2f}")                  # thousands separator
print(f"{0.256:.1%}")                         # x100, one decimal, %
print(f"{item=} {qty=}")                      # debug: name=repr(value)
print(f"{item!r}")                            # repr, with quotes
```

```console
coffee x3 = 13.50
coffee    |   3|
coffee....    4.50
1,234,567.89
25.6%
item='coffee' qty=3
'coffee'
```

- `<` left-aligns, `>` right-aligns and `^` centres. Numbers right-align by default, and strings left-align.
- A character before the alignment is the **fill**, as in `.<10` or `0>3`.
- `{x=}` is great for quick debugging prints. Remove them before you commit.

```quiz
{ "id": "q8", "type": "output",
  "prompt": "What does this print?",
  "code": "price = 1234.5\nlabel = \"ok\"\nprint(f\"{price:,.2f}\")\nprint(f\"{label:*^6}|{7:0>3}\")\nprint(f\"{0.256:.1%}\")",
  "answer": "1,234.50\n**ok**|007\n25.6%",
  "explanation": ",.2f adds thousands separators and exactly 2 decimals. *^6 centres \"ok\" in 6 characters, filling with *. 0>3 right-aligns 7 in 3 characters, filling with 0. .1% multiplies by 100 and keeps one decimal." }
```

## 6. Your turn: a settings parser

Config files, `.env` files and form posts are all "lines of `key = value`". You'll write the parser and a helper for comma-separated values. Expect the edges from this lesson: blank and whitespace-only lines, values that contain the separator, empty fields between commas, and empty input.

```exercise
PY.M03.L04.E1
```
