"""
Computer Science subject prompt — IBDP Computer Science HL/SL, AP Computer Science A,
AP Computer Science Principles, MYP Design.
"""

_KEYWORDS = (
    "computer science", "computer studies", "computing", "cs ", "ap cs",
    "programming", "coding", "software", "design technology",
)


def inject_if_match(course_name: str, extra: str) -> str:
    if not any(k in course_name.lower() for k in _KEYWORDS):
        return extra
    return extra + _build_prompt()


def _build_prompt() -> str:
    return """
## Computer Science technique (IB / AP)

### IB Pseudocode
IB uses its own pseudocode syntax — use it when writing algorithms for IB students:
- Assignment: `X = 5`
- Output: `output X`
- Input: `X = input()`
- If: `if X > 5 then ... end if`
- Loop (count): `loop N times ... end loop`
- Loop (while): `loop while X > 0 ... end loop`
- Array: `ARR[0]` (0-indexed), size declared as `ARR = new Array(10)`
- Method call: `OBJECT.method(param)`

Always write pseudocode in IB format for IB students; Python or Java for AP students.

### Algorithm design
- Before coding: define inputs, outputs, and the algorithm steps in plain English first
- Trace tables: walk through algorithm execution step by step — use a table with variable columns
- Big O notation: O(1), O(log n), O(n), O(n log n), O(n²) — know which applies to common algorithms
- Always consider: does the algorithm handle edge cases? (empty list, single element, duplicates)

### Data structures
- Arrays: fixed size, O(1) access, O(n) search
- Linked lists: dynamic, O(n) access, efficient insertion/deletion at known position
- Stacks (LIFO) and Queues (FIFO): push/pop vs enqueue/dequeue — know real-world applications
- Binary trees: left < root < right; traversals (inorder, preorder, postorder)
- Hash tables: O(1) average lookup; collision handling (chaining, open addressing)

### IB CS exam technique
- **Paper 1** (HL: 2h20 / SL: 1h30): structured questions on core topics — system design, data representation, networks, OOP
- **Paper 2** (HL only): case study — read the pre-released case study before the exam; questions require applying concepts to it
- **Paper 3** (HL only): object-oriented programming — write Java/pseudocode; know inheritance, polymorphism, encapsulation
- IA (Internal Assessment): build a software product for a real client; must include client consultation, design, implementation, testing, and evaluation

### OOP concepts
- Encapsulation: data + methods in one class; private vs public
- Inheritance: subclass inherits from superclass; `extends` in Java
- Polymorphism: same method name, different behaviour depending on object type
- Abstract classes and interfaces: define what subclasses MUST implement
- When explaining: give a code example AND a real-world analogy

### AP Computer Science A (Java)
- Focus areas: OOP, arrays, ArrayLists, 2D arrays, inheritance, recursion, sorting/searching
- FRQ types: method writing, class writing, array/ArrayList manipulation, 2D array
- Always trace through your code mentally before submitting — simple errors (off-by-one, wrong operator) cost marks

### AP Computer Science Principles
- Computational thinking, data representation, internet, algorithms, programming
- Create performance task: document your program's purpose, functionality, and algorithm clearly
- Written response: explain how your algorithm uses abstraction and handles data

### MYP Design (Grades 6–10)
- Criterion A (Inquiring and Analysing): research existing products and define the design problem
- Criterion B (Developing Ideas): generate multiple design options, justify the chosen one
- Criterion C (Creating): document the making process; problems encountered and solutions
- Criterion D (Evaluating): test against the design brief criteria; seek client/peer feedback
"""
