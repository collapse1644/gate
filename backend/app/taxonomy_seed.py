"""Official GATE 2027 CS + GA syllabus taxonomy.

Source (retrieved 2026-11-06):
  https://gate2027.iitm.ac.in/exam_papers_and_syllabus
  CS: https://gate2027.iitm.ac.in/static/doc/GATE2027_Syllabus/CS_GATE2027_Syllabus.pdf
  GA: https://gate2027.iitm.ac.in/static/doc/GATE2027_Syllabus/GA_GATE2027_Syllabus.pdf

The taxonomy below is an expansion of the *official* wording only. It does not
import third-party classifications. Subtopic and concept descriptions are study
aids, not official syllabus text; `official_text` on each section preserves the
source wording.
"""

from __future__ import annotations

OFFICIAL_SECTIONS: list[dict] = [
    {
        "code": "GA-1",
        "title": "Verbal Aptitude",
        "category": "General Aptitude",
        "subject": "General Aptitude",
        "text": (
            "Basic English grammar: tenses, articles, adjectives, prepositions, conjunctions, "
            "verb-noun agreement, and other parts of speech. Basic vocabulary: words, idioms, "
            "and phrases in context. Reading and comprehension, Narrative sequencing."
        ),
    },
    {
        "code": "GA-2",
        "title": "Quantitative Aptitude",
        "category": "General Aptitude",
        "subject": "General Aptitude",
        "text": (
            "Data interpretation: data graphs (bar graphs, pie charts, and other graphs "
            "representing data), 2-and 3-dimensional plots, maps, and tables. Numerical "
            "computation and estimation: ratios, percentages, powers, exponents and logarithms, "
            "permutations and combinations, and series. Mensuration and geometry, Elementary "
            "statistics and probability."
        ),
    },
    {
        "code": "GA-3",
        "title": "Analytical Aptitude",
        "category": "General Aptitude",
        "subject": "General Aptitude",
        "text": (
            "Logic: deduction and induction, Analogy, Numerical relations and reasoning."
        ),
    },
    {
        "code": "GA-4",
        "title": "Spatial Aptitude",
        "category": "General Aptitude",
        "subject": "General Aptitude",
        "text": (
            "Transformation of shapes: translation, rotation, scaling, mirroring, assembling, "
            "and grouping paper folding, cutting, and patterns in 2 and 3 dimensions."
        ),
    },
    {
        "code": "CS-1",
        "title": "Engineering Mathematics",
        "category": "Engineering Mathematics",
        "subject": "Engineering Mathematics",
        "text": (
            "Discrete Mathematics: Propositional and first order logic. Sets, relations, "
            "functions, partial orders and lattices. Monoids, Groups. Graphs: connectivity, "
            "matching, colouring. Combinatorics: counting, recurrence relations, generating "
            "functions. Linear Algebra: Matrices, determinants, system of linear equations, "
            "eigenvalues and eigenvectors, LU decomposition. Calculus: Limits, continuity and "
            "differentiability, Maxima and minima, Mean value theorem, Integration. Probability "
            "and Statistics: Random variables, Uniform, normal, exponential, Poisson and binomial "
            "distributions. Mean, median, mode and standard deviation. Conditional probability "
            "and Bayes theorem."
        ),
    },
    {
        "code": "CS-2",
        "title": "Digital Logic",
        "category": "Core Computer Science",
        "subject": "Digital Logic",
        "text": (
            "Boolean algebra and minimization – algebraic technique, Karnaugh map, tabular "
            "method. Design of combinational and sequential circuits. Number representation and "
            "arithmetic (fixed and floating point)."
        ),
    },
    {
        "code": "CS-3",
        "title": "Computer Organization and Architecture",
        "category": "Core Computer Science",
        "subject": "Computer Organization and Architecture",
        "text": (
            "Instruction set and addressing modes. Design of arithmetic and logic unit (ALU). "
            "Design of control unit – hardwired and microprogrammed. Memory interfacing and "
            "hierarchy: performance, cache memory mapping. I/O interface (interrupt and DMA). "
            "Instruction pipelining, pipeline hazards."
        ),
    },
    {
        "code": "CS-4",
        "title": "Programming and Data Structures",
        "category": "Core Computer Science",
        "subject": "Programming and Data Structures",
        "text": (
            "Programming in C. Recursion. Arrays, stacks, queues, linked lists, trees, binary "
            "search trees, binary heaps, graphs."
        ),
    },
    {
        "code": "CS-5",
        "title": "Algorithms",
        "category": "Core Computer Science",
        "subject": "Algorithms",
        "text": (
            "Searching, sorting, hashing. Asymptotic worst case time and space complexity. "
            "Algorithm design techniques: greedy, dynamic programming and divide-and-conquer. "
            "Graph traversals, minimum spanning trees, shortest paths."
        ),
    },
    {
        "code": "CS-6",
        "title": "Theory of Computation",
        "category": "Core Computer Science",
        "subject": "Theory of Computation",
        "text": (
            "Regular expressions and finite automata. Context-free grammars and push-down "
            "automata. Regular and context-free languages, pumping lemma. Turing machines and "
            "undecidability."
        ),
    },
    {
        "code": "CS-7",
        "title": "Compiler Design",
        "category": "Core Computer Science",
        "subject": "Compiler Design",
        "text": (
            "Lexical analysis, parsing, syntax-directed translation. Runtime environments. "
            "Intermediate code generation. Local optimisation, Data flow analyses: constant "
            "propagation, liveness analysis, common sub expression elimination."
        ),
    },
    {
        "code": "CS-8",
        "title": "Operating System",
        "category": "Core Computer Science",
        "subject": "Operating Systems",
        "text": (
            "System calls, processes, threads, inter-process communication, concurrency and "
            "synchronization. Deadlock. CPU and I/O scheduling. Memory management and virtual "
            "memory. File systems."
        ),
    },
    {
        "code": "CS-9",
        "title": "Databases",
        "category": "Core Computer Science",
        "subject": "Databases",
        "text": (
            "ER-model. Relational model: relational algebra, tuple calculus, SQL. Integrity "
            "constraints, normal forms. File organization, indexing (e.g., B and B+ trees). "
            "Transactions and concurrency control."
        ),
    },
    {
        "code": "CS-10",
        "title": "Computer Networks",
        "category": "Core Computer Science",
        "subject": "Computer Networks",
        "text": (
            "Principles of Layering; Basics of switching (circuit, packet and virtual circuit) "
            "and performance metrics; Data link layer: error detection, Medium Access Control, "
            "Ethernet; Distance vector and link state routing; IPv4 - Fragmentation, CIDR "
            "Notation, Network Address Translation; TCP- flow control and congestion control, "
            "socket API; DNS and HTTP."
        ),
    },
]

# subject -> topics -> subtopics -> concepts
# `keywords` strings are used by the deterministic classifier. Keep them
# discriminative: generic words are deliberately omitted.
TAXONOMY: list[dict] = [
    {
        "code": "GA",
        "name": "General Aptitude",
        "sections": ["GA-1", "GA-2", "GA-3", "GA-4"],
        "color": "#8b5cf6",
        "description": "Common 15-mark General Aptitude component of GATE 2027.",
        "topics": [
            {
                "name": "Verbal Aptitude",
                "section": "GA-1",
                "keywords": "grammar, vocabulary, comprehension, passage, idiom, synonym, antonym, tense, article, preposition, narration, analogy, intensity",
                "subtopics": [
                    {
                        "name": "Grammar and Usage",
                        "keywords": "tenses, articles, adjectives, prepositions, conjunctions, verb-noun agreement, parts of speech, grammatical error",
                        "concepts": [
                            ("Tense and aspect", "Correct tense usage in sentences.", "tenses, past perfect, present continuous"),
                            ("Articles and determiners", "Use of a, an, the and determiners.", "articles, determiners"),
                            ("Prepositions and conjunctions", "Appropriate linking words.", "prepositions, conjunctions"),
                            ("Subject-verb agreement", "Number agreement between subject and verb.", "verb-noun agreement, subject verb agreement"),
                        ],
                    },
                    {
                        "name": "Vocabulary in Context",
                        "keywords": "vocabulary, idiom, phrase, contextual meaning, synonym, antonym, word usage, analogy",
                        "concepts": [
                            ("Idioms and phrases", "Meaning of idioms in context.", "idiom, phrase"),
                            ("Contextual word meaning", "Infer word meaning from the sentence.", "synonym, antonym, contextual meaning"),
                        ],
                    },
                    {
                        "name": "Reading Comprehension",
                        "keywords": "reading comprehension, passage, inference, main idea, author's tone, narrative sequencing",
                        "concepts": [
                            ("Main idea and inference", "Identify central claim and valid inferences.", "main idea, inference, passage"),
                            ("Narrative sequencing", "Order events or sentences coherently.", "narrative sequencing, ordering"),
                        ],
                    },
                ],
            },
            {
                "name": "Quantitative Aptitude",
                "section": "GA-2",
                "keywords": "ratio, percentage, permutation, combination, logarithm, mensuration, geometry, probability, data interpretation, series",
                "subtopics": [
                    {
                        "name": "Data Interpretation",
                        "keywords": "bar graph, pie chart, data table, data interpretation, 2d plot, 3d plot, map, median, mean, mode, ratio, proportion, percentage",
                        "concepts": [
                            ("Charts and tables", "Extract and compare values from graphs and tables.", "bar graph, pie chart, table, chart"),
                            ("Plots and maps", "Read 2D/3D plots and maps.", "2d plot, 3d plot, map, graph"),
                        ],
                    },
                    {
                        "name": "Numerical Computation",
                        "keywords": "ratio, proportion, percentage, power, exponent, logarithm, permutation, combination, series, estimation, median, mean",
                        "concepts": [
                            ("Ratios and percentages", "Proportional reasoning and percentage change.", "ratio, percentage, proportion"),
                            ("Powers and logarithms", "Exponent and logarithm manipulation.", "exponent, logarithm, log"),
                            ("Counting", "Permutations and combinations.", "permutation, combination, counting"),
                            ("Series and estimation", "Sequences, sums and approximation.", "series, summation, estimation"),
                        ],
                    },
                    {
                        "name": "Mensuration and Geometry",
                        "keywords": "area, volume, perimeter, circle, triangle, rectangle, cylinder, cone, sphere, mensuration, geometry",
                        "concepts": [
                            ("Plane geometry", "Angles, triangles, circles and polygons.", "triangle, circle, polygon, angle"),
                            ("Solid mensuration", "Surface area and volume of solids.", "volume, surface area, cylinder, cone, sphere"),
                        ],
                    },
                    {
                        "name": "Elementary Statistics and Probability",
                        "keywords": "mean, median, mode, standard deviation, probability, average, variance, permutation, combination",
                        "concepts": [
                            ("Averages", "Mean, median and mode.", "mean, median, mode, average"),
                            ("Basic probability", "Simple probability and counting outcomes.", "probability, outcomes"),
                            ("Dispersion", "Standard deviation and variance.", "standard deviation, variance"),
                        ],
                    },
                ],
            },
            {
                "name": "Analytical Aptitude",
                "section": "GA-3",
                "keywords": "deduction, induction, analogy, numerical relation, logical reasoning, puzzle",
                "subtopics": [
                    {
                        "name": "Logic and Deduction",
                        "keywords": "deduction, induction, syllogism, logical conclusion, assumption, puzzle, analogy",
                        "concepts": [
                            ("Deductive reasoning", "Derive necessary conclusions.", "deduction, syllogism, conclusion"),
                            ("Inductive reasoning", "Identify patterns and generalizations.", "induction, pattern"),
                        ],
                    },
                    {
                        "name": "Analogy and Numerical Relations",
                        "keywords": "analogy, numerical relation, number series, coding decoding, blood relation, direction, intensity",
                        "concepts": [
                            ("Analogies", "Relational mapping between pairs.", "analogy, relation"),
                            ("Numerical reasoning", "Number patterns and relations.", "numerical relation, number series"),
                        ],
                    },
                ],
            },
            {
                "name": "Spatial Aptitude",
                "section": "GA-4",
                "keywords": "rotation, translation, scaling, mirror image, paper folding, paper cutting, spatial pattern",
                "subtopics": [
                    {
                        "name": "Shape Transformation",
                        "keywords": "translation, rotation, scaling, mirroring, assembling, grouping, reflection",
                        "concepts": [
                            ("Rotation and reflection", "Predict transformed shapes.", "rotation, mirror image, reflection"),
                            ("Scaling and assembly", "Resize, group and assemble shapes.", "scaling, assembling, grouping"),
                        ],
                    },
                    {
                        "name": "Paper Folding and Cutting",
                        "keywords": "paper folding, paper cutting, unfold, pattern, 2d, 3d",
                        "concepts": [
                            ("Fold and punch patterns", "Trace cuts through folded paper.", "paper folding, paper cutting, unfold"),
                            ("3D visualization", "Reason about spatial patterns in 3D.", "3d, spatial pattern"),
                        ],
                    },
                ],
            },
        ],
    },
    {
        "code": "EM",
        "name": "Engineering Mathematics",
        "sections": ["CS-1"],
        "color": "#0ea5e9",
        "description": "Discrete mathematics, linear algebra, calculus, probability and statistics.",
        "topics": [
            {
                "name": "Discrete Mathematics",
                "section": "CS-1",
                "keywords": "discrete mathematics, logic, set, relation, lattice, group, graph theory, combinatorics",
                "subtopics": [
                    {
                        "name": "Propositional and First Order Logic",
                        "keywords": "propositional logic, first order logic, predicate logic, truth table, tautology, validity, quantifier, satisfiability",
                        "concepts": [
                            ("Propositional connectives", "Truth tables, tautology and equivalence.", "truth table, tautology, implication, equivalence"),
                            ("Quantifiers", "Universal and existential quantification.", "forall, exists, quantifier, predicate"),
                            ("Validity and satisfiability", "Determine logical consequence and models.", "validity, satisfiability, logical consequence"),
                        ],
                    },
                    {
                        "name": "Sets, Relations and Functions",
                        "keywords": "set, subset, power set, relation, equivalence relation, function, injection, surjection, bijection, cardinality",
                        "concepts": [
                            ("Set operations", "Union, intersection, power set and cardinality.", "union, intersection, power set, cardinality"),
                            ("Relations", "Reflexive, symmetric, transitive, equivalence.", "equivalence relation, reflexive, symmetric, transitive"),
                            ("Functions", "Injective, surjective and bijective functions.", "injective, surjective, bijective, function"),
                        ],
                    },
                    {
                        "name": "Partial Orders and Lattices",
                        "keywords": "partial order, poset, hasse diagram, lattice, distributive lattice, complement, boolean algebra",
                        "concepts": [
                            ("Posets and Hasse diagrams", "Partial order structure and extremal elements.", "poset, hasse diagram, maximal, minimal"),
                            ("Lattices", "Meet, join and lattice properties.", "lattice, meet, join, distributive"),
                        ],
                    },
                    {
                        "name": "Monoids and Groups",
                        "keywords": "monoid, semigroup, group, subgroup, cyclic group, abelian group, coset, homomorphism",
                        "concepts": [
                            ("Algebraic structures", "Closure, associativity, identity and inverse.", "monoid, semigroup, group"),
                            ("Group properties", "Cyclic, abelian, subgroup and order.", "cyclic group, abelian, subgroup, order"),
                        ],
                    },
                    {
                        "name": "Graph Theory",
                        "keywords": "graph, tree, connectivity, cut vertex, matching, coloring, euler, hamiltonian, planar graph, bipartite",
                        "concepts": [
                            ("Connectivity", "Paths, cuts and connected components.", "connectivity, cut vertex, component"),
                            ("Matching", "Maximum and perfect matchings.", "matching, perfect matching, hall"),
                            ("Colouring", "Chromatic number and graph colouring.", "coloring, chromatic number"),
                            ("Special graphs", "Trees, Eulerian, Hamiltonian, planar and bipartite graphs.", "tree, eulerian, hamiltonian, planar, bipartite"),
                        ],
                    },
                    {
                        "name": "Combinatorics",
                        "keywords": "counting, pigeonhole, recurrence relation, generating function, inclusion exclusion, permutation, combination",
                        "concepts": [
                            ("Counting principles", "Product, sum, inclusion-exclusion, pigeonhole.", "counting, inclusion exclusion, pigeonhole"),
                            ("Recurrence relations", "Solve linear recurrences.", "recurrence relation, characteristic equation"),
                            ("Generating functions", "Ordinary and exponential generating functions.", "generating function, coefficient"),
                        ],
                    },
                ],
            },
            {
                "name": "Linear Algebra",
                "section": "CS-1",
                "keywords": "matrix, determinant, eigenvalue, eigenvector, linear equations, lu decomposition, rank, vector space",
                "subtopics": [
                    {
                        "name": "Matrices and Determinants",
                        "keywords": "matrix, determinant, transpose, inverse, rank, trace, minor, cofactor",
                        "concepts": [
                            ("Matrix operations", "Multiplication, transpose, inverse and trace.", "matrix multiplication, transpose, inverse, trace"),
                            ("Determinants and rank", "Determinant properties and rank.", "determinant, rank, minor, cofactor"),
                        ],
                    },
                    {
                        "name": "Systems of Linear Equations",
                        "keywords": "system of linear equations, consistency, gaussian elimination, rank, homogeneous, unique solution, infinite solutions",
                        "concepts": [
                            ("Consistency", "Existence and number of solutions.", "consistency, unique solution, infinite solutions"),
                            ("Elimination", "Gaussian elimination and row reduction.", "gaussian elimination, row reduction, pivot"),
                        ],
                    },
                    {
                        "name": "Eigenvalues and Eigenvectors",
                        "keywords": "eigenvalue, eigenvector, characteristic polynomial, diagonalization, similarity, cayley hamilton",
                        "concepts": [
                            ("Characteristic equation", "Compute eigenvalues and eigenvectors.", "characteristic polynomial, eigenvalue, eigenvector"),
                            ("Diagonalization", "Similarity and diagonalizability.", "diagonalization, similarity"),
                        ],
                    },
                    {
                        "name": "LU Decomposition",
                        "keywords": "lu decomposition, lower triangular, upper triangular, factorization, pivot",
                        "concepts": [
                            ("LU factorization", "Decompose a matrix into L and U.", "lu decomposition, factorization, triangular"),
                        ],
                    },
                ],
            },
            {
                "name": "Calculus",
                "section": "CS-1",
                "keywords": "limit, continuity, differentiability, maxima, minima, mean value theorem, integration, derivative",
                "subtopics": [
                    {
                        "name": "Limits, Continuity and Differentiability",
                        "keywords": "limit, continuity, differentiability, l hopital, derivative, piecewise function",
                        "concepts": [
                            ("Limits", "Evaluate limits and indeterminate forms.", "limit, l hopital, indeterminate"),
                            ("Continuity and differentiability", "Check continuity and derivative existence.", "continuity, differentiability, piecewise"),
                        ],
                    },
                    {
                        "name": "Maxima and Minima",
                        "keywords": "maxima, minima, critical point, optimization, second derivative, saddle",
                        "concepts": [
                            ("Critical points", "First and second derivative tests.", "critical point, maxima, minima, derivative test"),
                        ],
                    },
                    {
                        "name": "Mean Value Theorem",
                        "keywords": "mean value theorem, rolle theorem, average rate, existence",
                        "concepts": [
                            ("Rolle and Lagrange MVT", "Existence of points with given derivative.", "rolle theorem, mean value theorem"),
                        ],
                    },
                    {
                        "name": "Integration",
                        "keywords": "integration, definite integral, area under curve, substitution, integration by parts",
                        "concepts": [
                            ("Definite integrals", "Evaluate integrals and areas.", "definite integral, area, substitution, integration by parts"),
                        ],
                    },
                ],
            },
            {
                "name": "Probability and Statistics",
                "section": "CS-1",
                "keywords": "probability, random variable, distribution, mean, median, mode, standard deviation, bayes theorem",
                "subtopics": [
                    {
                        "name": "Random Variables and Distributions",
                        "keywords": "random variable, uniform distribution, normal distribution, exponential distribution, poisson distribution, binomial distribution, expectation, variance",
                        "concepts": [
                            ("Discrete distributions", "Binomial and Poisson distributions.", "binomial, poisson, pmf"),
                            ("Continuous distributions", "Uniform, normal and exponential distributions.", "uniform, normal, exponential, pdf"),
                            ("Expectation and variance", "Compute moments of random variables.", "expectation, variance, moment"),
                        ],
                    },
                    {
                        "name": "Descriptive Statistics",
                        "keywords": "mean, median, mode, standard deviation, variance, quartile, skewness",
                        "concepts": [
                            ("Central tendency", "Mean, median and mode.", "mean, median, mode"),
                            ("Dispersion", "Standard deviation and variance.", "standard deviation, variance, quartile"),
                        ],
                    },
                    {
                        "name": "Conditional Probability and Bayes Theorem",
                        "keywords": "conditional probability, bayes theorem, independence, prior, posterior, total probability",
                        "concepts": [
                            ("Conditional probability", "Dependence and independence.", "conditional probability, independence"),
                            ("Bayes theorem", "Posterior probability from priors.", "bayes theorem, prior, posterior, total probability"),
                        ],
                    },
                ],
            },
        ],
    },
    {
        "code": "DL",
        "name": "Digital Logic",
        "sections": ["CS-2"],
        "color": "#f59e0b",
        "description": "Boolean algebra, combinational/sequential circuits and number representation.",
        "topics": [
            {
                "name": "Boolean Algebra and Minimization",
                "section": "CS-2",
                "keywords": "boolean algebra, karnaugh map, k map, tabular method, quine mccluskey, minimization, don't care",
                "subtopics": [
                    {
                        "name": "Boolean Algebra",
                        "keywords": "boolean algebra, boolean expression, identity, duality, canonical form, sop, pos",
                        "concepts": [
                            ("Boolean identities", "Simplify expressions algebraically.", "boolean identity, duality, demorgan"),
                            ("Canonical forms", "SOP, POS and minterms/maxterms.", "sop, pos, minterm, maxterm"),
                        ],
                    },
                    {
                        "name": "Karnaugh Map and Tabular Minimization",
                        "keywords": "karnaugh map, k map, don't care, prime implicant, quine mccluskey, tabular method, minimization",
                        "concepts": [
                            ("K-map grouping", "Minimize using prime implicants.", "k map, grouping, prime implicant, don't care"),
                            ("Quine-McCluskey", "Tabular minimization and essential prime implicants.", "quine mccluskey, tabular method, essential prime implicant"),
                        ],
                    },
                ],
            },
            {
                "name": "Combinational Circuits",
                "section": "CS-2",
                "keywords": "combinational circuit, multiplexer, decoder, encoder, adder, subtractor, comparator, logic gate",
                "subtopics": [
                    {
                        "name": "Gates and Adders",
                        "keywords": "logic gate, nand, nor, xor, half adder, full adder, ripple carry, carry lookahead",
                        "concepts": [
                            ("Logic gates", "Universal gates and gate-level realization.", "nand, nor, xor, universal gate"),
                            ("Adders and subtractors", "Ripple carry, carry lookahead and subtraction.", "half adder, full adder, ripple carry, carry lookahead"),
                        ],
                    },
                    {
                        "name": "Multiplexers and Decoders",
                        "keywords": "multiplexer, mux, decoder, encoder, demultiplexer, comparator, function realization",
                        "concepts": [
                            ("Multiplexer realization", "Implement Boolean functions with MUXes.", "multiplexer, mux, function realization"),
                            ("Decoders and encoders", "Build decoders/encoders and use them for logic.", "decoder, encoder, demultiplexer"),
                        ],
                    },
                ],
            },
            {
                "name": "Sequential Circuits",
                "section": "CS-2",
                "keywords": "sequential circuit, flip flop, latch, register, counter, state machine, finite state machine, excitation table",
                "subtopics": [
                    {
                        "name": "Latches and Flip-Flops",
                        "keywords": "latch, flip flop, sr, jk, d flip flop, t flip flop, race around, excitation table",
                        "concepts": [
                            ("Latch and flip-flop behaviour", "Level/edge triggering and truth tables.", "latch, flip flop, edge triggered"),
                            ("Flip-flop conversion", "Excitation tables and conversion between types.", "excitation table, jk, d flip flop, t flip flop"),
                        ],
                    },
                    {
                        "name": "Registers and Counters",
                        "keywords": "register, shift register, counter, ripple counter, synchronous counter, modulo counter",
                        "concepts": [
                            ("Counters", "Synchronous/asynchronous and modulus counting.", "counter, ripple counter, modulo"),
                            ("Shift registers", "Serial/parallel shifting and sequence generation.", "shift register, serial, parallel"),
                        ],
                    },
                    {
                        "name": "Finite State Machines",
                        "keywords": "state machine, finite state machine, state diagram, state table, mealy, moore, sequence detector",
                        "concepts": [
                            ("Mealy and Moore machines", "Design output logic for state machines.", "mealy, moore, state diagram"),
                            ("Sequence detection", "Design detectors with flip-flops.", "sequence detector, state table"),
                        ],
                    },
                ],
            },
            {
                "name": "Number Representation and Arithmetic",
                "section": "CS-2",
                "keywords": "number representation, fixed point, floating point, ieee 754, two's complement, signed magnitude, overflow, arithmetic",
                "subtopics": [
                    {
                        "name": "Fixed-Point Representation",
                        "keywords": "two's complement, one's complement, signed magnitude, fixed point, overflow, range, binary arithmetic",
                        "concepts": [
                            ("Signed representations", "Two's complement, one's complement and sign-magnitude.", "two's complement, signed magnitude, one's complement"),
                            ("Fixed-point arithmetic", "Addition, subtraction and overflow detection.", "fixed point, overflow, binary arithmetic"),
                        ],
                    },
                    {
                        "name": "Floating-Point Representation",
                        "keywords": "ieee 754, floating point, mantissa, exponent, bias, normalized, denormal, rounding",
                        "concepts": [
                            ("IEEE 754 format", "Sign, exponent and mantissa fields.", "ieee 754, mantissa, exponent, bias"),
                            ("Floating-point arithmetic", "Normalization, rounding and special values.", "normalized, denormal, rounding, nan"),
                        ],
                    },
                ],
            },
        ],
    },
    {
        "code": "COA",
        "name": "Computer Organization and Architecture",
        "sections": ["CS-3"],
        "color": "#ef4444",
        "description": "ISA, datapath/control, memory hierarchy, I/O and pipelining.",
        "topics": [
            {
                "name": "Instruction Set and Addressing Modes",
                "section": "CS-3",
                "keywords": "instruction set, addressing mode, isa, opcode, operand, risc, cisc, instruction format",
                "subtopics": [
                    {
                        "name": "Instruction Formats",
                        "keywords": "instruction format, opcode, operand, immediate, register, risc, cisc",
                        "concepts": [
                            ("Instruction encoding", "Opcode and operand field layout.", "opcode, instruction format, encoding"),
                            ("RISC vs CISC", "Design trade-offs.", "risc, cisc"),
                        ],
                    },
                    {
                        "name": "Addressing Modes",
                        "keywords": "addressing mode, immediate, direct, indirect, indexed, register indirect, pc relative, effective address",
                        "concepts": [
                            ("Effective address", "Compute operands for each mode.", "effective address, indexed, indirect"),
                            ("Mode identification", "Classify instructions by addressing mode.", "addressing mode, immediate, relative"),
                        ],
                    },
                ],
            },
            {
                "name": "ALU Design",
                "section": "CS-3",
                "keywords": "alu, arithmetic logic unit, adder, shifter, flag, status register, datapath",
                "subtopics": [
                    {
                        "name": "Arithmetic and Logic Datapath",
                        "keywords": "alu, adder, subtractor, shifter, zero flag, carry flag, overflow flag, datapath",
                        "concepts": [
                            ("ALU operations", "Arithmetic/logic operations and flags.", "alu, flag, shift, add"),
                            ("Datapath design", "Connect registers and functional units.", "datapath, bus, register transfer"),
                        ],
                    },
                ],
            },
            {
                "name": "Control Unit Design",
                "section": "CS-3",
                "keywords": "control unit, hardwired control, microprogrammed control, microinstruction, microprogram, control signal",
                "subtopics": [
                    {
                        "name": "Hardwired and Microprogrammed Control",
                        "keywords": "hardwired control, microprogrammed control, microinstruction, control store, horizontal microcode, vertical microcode",
                        "concepts": [
                            ("Hardwired control", "Sequencing with logic and counters.", "hardwired control, control signal"),
                            ("Microprogramming", "Microinstruction formats and sequencing.", "microprogram, microinstruction, control store"),
                        ],
                    },
                ],
            },
            {
                "name": "Memory Hierarchy and Interfacing",
                "section": "CS-3",
                "keywords": "cache, memory hierarchy, cache mapping, hit ratio, miss penalty, locality, main memory, associative, set associative",
                "subtopics": [
                    {
                        "name": "Cache Memory",
                        "keywords": "cache memory, direct mapped, fully associative, set associative, tag, index, offset, replacement policy, write policy",
                        "concepts": [
                            ("Cache mapping", "Direct, associative and set-associative mapping.", "direct mapped, fully associative, set associative, tag, index"),
                            ("Cache performance", "Hit ratio, AMAT and miss penalty.", "hit ratio, miss penalty, amat"),
                            ("Write policies", "Write-through and write-back.", "write through, write back, dirty bit"),
                        ],
                    },
                    {
                        "name": "Memory Interfacing and Performance",
                        "keywords": "memory interfacing, memory chip, address decoding, ram, rom, memory bandwidth, interleaving, performance",
                        "concepts": [
                            ("Address decoding", "Chip select and memory mapping.", "address decoding, chip select, ram, rom"),
                            ("Memory performance", "Bandwidth and interleaving.", "memory bandwidth, interleaving, access time"),
                        ],
                    },
                ],
            },
            {
                "name": "I/O Interface",
                "section": "CS-3",
                "keywords": "io interface, interrupt, dma, programmed io, memory mapped io, polling, device controller",
                "subtopics": [
                    {
                        "name": "Interrupts and DMA",
                        "keywords": "interrupt, vectored interrupt, interrupt latency, dma, cycle stealing, burst mode, programmed io, polling",
                        "concepts": [
                            ("Interrupt-driven I/O", "Interrupt handling and priority.", "interrupt, vectored interrupt, polling"),
                            ("DMA", "Direct memory access and cycle stealing.", "dma, cycle stealing, burst mode"),
                        ],
                    },
                ],
            },
            {
                "name": "Pipelining and Hazards",
                "section": "CS-3",
                "keywords": "pipeline, pipelining, hazard, data hazard, control hazard, structural hazard, forwarding, stall, speedup",
                "subtopics": [
                    {
                        "name": "Pipeline Performance",
                        "keywords": "pipeline, speedup, throughput, latency, ideal cpi, pipeline register, depth",
                        "concepts": [
                            ("Speedup and throughput", "Compute pipeline performance.", "speedup, throughput, cpi"),
                            ("Pipeline scheduling", "Reservation tables and timing diagrams.", "reservation table, pipeline scheduling"),
                        ],
                    },
                    {
                        "name": "Pipeline Hazards",
                        "keywords": "data hazard, control hazard, structural hazard, forwarding, bypassing, stall, branch penalty, delayed branch",
                        "concepts": [
                            ("Data hazards", "RAW/WAW/WAR and forwarding.", "data hazard, raw, forwarding, stall"),
                            ("Control hazards", "Branch penalties and prediction.", "control hazard, branch penalty, delayed branch"),
                            ("Structural hazards", "Resource conflicts.", "structural hazard, resource conflict"),
                        ],
                    },
                ],
            },
        ],
    },
    {
        "code": "PDS",
        "name": "Programming and Data Structures",
        "sections": ["CS-4"],
        "color": "#10b981",
        "description": "C programming, recursion and fundamental data structures.",
        "topics": [
            {
                "name": "Programming in C",
                "section": "CS-4",
                "keywords": "c programming, pointer, array, string, structure, union, function, scope, storage class, dynamic memory",
                "subtopics": [
                    {
                        "name": "C Fundamentals",
                        "keywords": "c program, operator precedence, type conversion, loop, conditional, switch, function call, parameter passing",
                        "concepts": [
                            ("Expressions and control flow", "Operator precedence, loops and conditionals.", "operator precedence, loop, switch"),
                            ("Functions and parameter passing", "Call by value/reference, recursion.", "function call, call by value, parameter passing"),
                        ],
                    },
                    {
                        "name": "Pointers and Memory",
                        "keywords": "pointer, pointer arithmetic, array pointer, function pointer, malloc, calloc, free, dangling pointer, memory leak",
                        "concepts": [
                            ("Pointer arithmetic", "Pointers, arrays and indirection.", "pointer arithmetic, dereference, array pointer"),
                            ("Dynamic memory", "malloc/free and lifetime.", "malloc, calloc, free, memory leak"),
                        ],
                    },
                    {
                        "name": "Structures and Strings",
                        "keywords": "structure, union, typedef, string, char array, null terminator, structure padding",
                        "concepts": [
                            ("Structures and unions", "Layout, padding and member access.", "structure, union, padding"),
                            ("C strings", "Null-terminated strings and library functions.", "string, null terminator, strlen"),
                        ],
                    },
                ],
            },
            {
                "name": "Recursion",
                "section": "CS-4",
                "keywords": "recursion, recursive function, base case, call stack, tail recursion, recurrence, recursion tree",
                "subtopics": [
                    {
                        "name": "Recursive Algorithms",
                        "keywords": "recursion, base case, recursive call, recursion tree, tail recursion, stack frame, fibonacci, tower of hanoi",
                        "concepts": [
                            ("Recursion tracing", "Trace calls and return values.", "recursion, call stack, base case"),
                            ("Recursion to iteration", "Tail recursion and stack usage.", "tail recursion, stack frame"),
                        ],
                    },
                ],
            },
            {
                "name": "Arrays and Strings",
                "section": "CS-4",
                "keywords": "array, 2d array, row major, column major, sparse matrix, string matching, prefix sum",
                "subtopics": [
                    {
                        "name": "Arrays and Storage",
                        "keywords": "array, row major, column major, address calculation, sparse matrix, dynamic array",
                        "concepts": [
                            ("Array address calculation", "Row/column-major offsets.", "row major, column major, address calculation"),
                            ("Special arrays", "Sparse and multidimensional arrays.", "sparse matrix, 2d array"),
                        ],
                    },
                ],
            },
            {
                "name": "Stacks and Queues",
                "section": "CS-4",
                "keywords": "stack, queue, push, pop, enqueue, dequeue, circular queue, priority queue, infix, postfix, expression evaluation",
                "subtopics": [
                    {
                        "name": "Stack Applications",
                        "keywords": "stack, push, pop, infix, postfix, prefix, expression evaluation, balanced parentheses, next greater element",
                        "concepts": [
                            ("Expression conversion", "Infix to postfix/prefix.", "infix, postfix, prefix, expression evaluation"),
                            ("Stack-based problems", "Parentheses and monotonic stack.", "balanced parentheses, next greater element, stack"),
                        ],
                    },
                    {
                        "name": "Queues",
                        "keywords": "queue, circular queue, dequeue, priority queue, enqueue, front, rear",
                        "concepts": [
                            ("Queue implementations", "Linear, circular and deque.", "circular queue, dequeue, front, rear"),
                            ("Priority queues", "Heap-backed scheduling.", "priority queue, heap"),
                        ],
                    },
                ],
            },
            {
                "name": "Linked Lists",
                "section": "CS-4",
                "keywords": "linked list, singly linked, doubly linked, circular linked, node, pointer, reversal, cycle detection",
                "subtopics": [
                    {
                        "name": "Linked List Operations",
                        "keywords": "singly linked list, doubly linked list, circular list, insertion, deletion, reversal, merge, cycle detection, floyd",
                        "concepts": [
                            ("List manipulation", "Insert, delete, reverse and merge.", "linked list, reversal, merge"),
                            ("Cycle detection", "Floyd's and hashing approaches.", "cycle detection, floyd, slow fast pointer"),
                        ],
                    },
                ],
            },
            {
                "name": "Trees and Binary Search Trees",
                "section": "CS-4",
                "keywords": "tree, binary tree, binary search tree, bst, traversal, inorder, preorder, postorder, height, avl",
                "subtopics": [
                    {
                        "name": "Binary Trees",
                        "keywords": "binary tree, inorder, preorder, postorder, level order, height, diameter, full binary tree, complete binary tree",
                        "concepts": [
                            ("Tree traversals", "Recursive and iterative traversals.", "inorder, preorder, postorder, level order"),
                            ("Tree properties", "Height, diameter and node counts.", "height, diameter, leaf, complete binary tree"),
                        ],
                    },
                    {
                        "name": "Binary Search Trees",
                        "keywords": "binary search tree, bst, search, insert, delete, predecessor, successor, balanced bst, avl",
                        "concepts": [
                            ("BST operations", "Search, insert and delete.", "bst, search, insert, delete"),
                            ("Balanced trees", "AVL rotations and balance.", "avl, rotation, balance factor"),
                        ],
                    },
                ],
            },
            {
                "name": "Binary Heaps",
                "section": "CS-4",
                "keywords": "heap, min heap, max heap, heapify, build heap, priority queue, heap sort",
                "subtopics": [
                    {
                        "name": "Heap Operations",
                        "keywords": "binary heap, min heap, max heap, heapify, insert, extract min, build heap, array representation",
                        "concepts": [
                            ("Heap property", "Array representation and indices.", "heap, array representation, parent child"),
                            ("Heap operations", "Insert, extract and heapify.", "heapify, extract min, build heap"),
                        ],
                    },
                ],
            },
            {
                "name": "Graphs",
                "section": "CS-4",
                "keywords": "graph representation, adjacency matrix, adjacency list, directed graph, undirected graph, degree, path",
                "subtopics": [
                    {
                        "name": "Graph Representation",
                        "keywords": "adjacency matrix, adjacency list, directed graph, undirected graph, weighted graph, degree, edge list",
                        "concepts": [
                            ("Graph storage", "Adjacency matrix vs list.", "adjacency matrix, adjacency list"),
                            ("Graph properties", "Degree, paths and connectivity basics.", "degree, path, directed graph"),
                        ],
                    },
                ],
            },
        ],
    },
    {
        "code": "ALGO",
        "name": "Algorithms",
        "sections": ["CS-5"],
        "color": "#6366f1",
        "description": "Searching, sorting, hashing, complexity and algorithm design paradigms.",
        "topics": [
            {
                "name": "Searching",
                "section": "CS-5",
                "keywords": "searching, binary search, linear search, lower bound, upper bound, rotated array, search space",
                "subtopics": [
                    {
                        "name": "Binary Search",
                        "keywords": "binary search, sorted array, lower bound, upper bound, rotated sorted array, search space, predicate search",
                        "concepts": [
                            ("Binary search variants", "Boundary and predicate formulations.", "binary search, lower bound, upper bound"),
                            ("Rotated arrays", "Search in rotated sorted arrays.", "rotated sorted array, pivot"),
                        ],
                    },
                ],
            },
            {
                "name": "Sorting",
                "section": "CS-5",
                "keywords": "sorting, quicksort, mergesort, heapsort, insertion sort, selection sort, counting sort, radix sort, stability",
                "subtopics": [
                    {
                        "name": "Comparison Sorting",
                        "keywords": "quicksort, mergesort, heapsort, insertion sort, selection sort, bubble sort, comparison, stability, in place",
                        "concepts": [
                            ("Divide-and-conquer sorts", "Merge sort and quicksort.", "mergesort, quicksort, partition"),
                            ("Elementary sorts", "Insertion, selection and bubble sort.", "insertion sort, selection sort, bubble sort"),
                            ("Sorting properties", "Stability, in-place and comparisons.", "stability, in place, comparison sort"),
                        ],
                    },
                    {
                        "name": "Linear-Time Sorting",
                        "keywords": "counting sort, radix sort, bucket sort, linear time, non comparison",
                        "concepts": [
                            ("Counting and radix sort", "Non-comparison sorting.", "counting sort, radix sort, bucket sort"),
                        ],
                    },
                ],
            },
            {
                "name": "Hashing",
                "section": "CS-5",
                "keywords": "hashing, hash function, collision, chaining, open addressing, linear probing, quadratic probing, double hashing, load factor",
                "subtopics": [
                    {
                        "name": "Hash Tables",
                        "keywords": "hash table, hash function, collision resolution, chaining, open addressing, linear probing, quadratic probing, double hashing, load factor, universal hashing",
                        "concepts": [
                            ("Collision resolution", "Chaining vs open addressing.", "chaining, open addressing, probing"),
                            ("Hash performance", "Load factor and expected probes.", "load factor, expected probes, universal hashing"),
                        ],
                    },
                ],
            },
            {
                "name": "Asymptotic Complexity",
                "section": "CS-5",
                "keywords": "asymptotic, big o, omega, theta, time complexity, space complexity, recurrence, master theorem, amortized",
                "subtopics": [
                    {
                        "name": "Complexity Analysis",
                        "keywords": "big o, big omega, big theta, time complexity, space complexity, best case, worst case, average case, amortized analysis",
                        "concepts": [
                            ("Asymptotic notation", "O, Omega, Theta and little-o.", "big o, omega, theta, little o"),
                            ("Amortized analysis", "Aggregate and accounting methods.", "amortized, aggregate analysis"),
                        ],
                    },
                    {
                        "name": "Recurrence Relations in Algorithms",
                        "keywords": "recurrence, master theorem, recursion tree, substitution method, divide and conquer recurrence",
                        "concepts": [
                            ("Master theorem", "Solve divide-and-conquer recurrences.", "master theorem, recurrence"),
                            ("Recursion trees", "Sum costs level by level.", "recursion tree, substitution method"),
                        ],
                    },
                ],
            },
            {
                "name": "Greedy Algorithms",
                "section": "CS-5",
                "keywords": "greedy, activity selection, fractional knapsack, huffman, exchange argument, matroid",
                "subtopics": [
                    {
                        "name": "Greedy Design",
                        "keywords": "greedy choice, activity selection, fractional knapsack, huffman coding, interval scheduling, exchange argument",
                        "concepts": [
                            ("Greedy choice property", "Prove optimal substructure.", "greedy choice, exchange argument"),
                            ("Classic greedy problems", "Scheduling, knapsack and Huffman.", "activity selection, fractional knapsack, huffman"),
                        ],
                    },
                ],
            },
            {
                "name": "Dynamic Programming",
                "section": "CS-5",
                "keywords": "dynamic programming, memoization, optimal substructure, overlapping subproblems, knapsack, lcs, matrix chain, dp table",
                "subtopics": [
                    {
                        "name": "DP Formulation",
                        "keywords": "dynamic programming, memoization, tabulation, state, transition, optimal substructure, overlapping subproblems",
                        "concepts": [
                            ("State and transition", "Define DP state and recurrence.", "dp state, transition, memoization"),
                            ("Classic DP", "Knapsack, LCS, LIS, matrix chain.", "0/1 knapsack, lcs, lis, matrix chain"),
                        ],
                    },
                ],
            },
            {
                "name": "Divide and Conquer",
                "section": "CS-5",
                "keywords": "divide and conquer, divide, conquer, combine, merge sort, quicksort, closest pair, median of medians",
                "subtopics": [
                    {
                        "name": "Divide-and-Conquer Design",
                        "keywords": "divide and conquer, merge sort, quicksort, closest pair, median of medians, multiplication, recurrence",
                        "concepts": [
                            ("Divide-and-conquer paradigm", "Split, solve and combine.", "divide and conquer, combine"),
                            ("Selection", "Median of medians and order statistics.", "median of medians, order statistic"),
                        ],
                    },
                ],
            },
            {
                "name": "Graph Traversals",
                "section": "CS-5",
                "keywords": "bfs, dfs, breadth first search, depth first search, topological sort, connected components, articulation point, bridge",
                "subtopics": [
                    {
                        "name": "BFS and DFS",
                        "keywords": "bfs, dfs, breadth first, depth first, queue, stack, topological sort, cycle detection, connected components",
                        "concepts": [
                            ("Traversal order", "BFS/DFS trees and visitation.", "bfs, dfs, traversal"),
                            ("Applications", "Topological sort, cycles and components.", "topological sort, cycle detection, connected components"),
                        ],
                    },
                    {
                        "name": "Articulation Points and Bridges",
                        "keywords": "articulation point, bridge, biconnected, low link, tarjan, cut vertex",
                        "concepts": [
                            ("Low-link values", "Find articulation points and bridges.", "articulation point, bridge, low link"),
                        ],
                    },
                ],
            },
            {
                "name": "Minimum Spanning Trees",
                "section": "CS-5",
                "keywords": "minimum spanning tree, mst, kruskal, prim, cut property, cycle property, union find",
                "subtopics": [
                    {
                        "name": "MST Algorithms",
                        "keywords": "kruskal, prim, union find, disjoint set, cut property, cycle property, minimum spanning tree",
                        "concepts": [
                            ("Kruskal and Prim", "Greedy MST construction.", "kruskal, prim, union find"),
                            ("MST properties", "Cut and cycle properties.", "cut property, cycle property, mst"),
                        ],
                    },
                ],
            },
            {
                "name": "Shortest Paths",
                "section": "CS-5",
                "keywords": "shortest path, dijkstra, bellman ford, floyd warshall, negative weight, relaxation, all pairs",
                "subtopics": [
                    {
                        "name": "Single-Source Shortest Paths",
                        "keywords": "dijkstra, bellman ford, relaxation, negative edge, priority queue, single source",
                        "concepts": [
                            ("Dijkstra", "Non-negative shortest paths.", "dijkstra, relaxation, priority queue"),
                            ("Bellman-Ford", "Negative edges and cycle detection.", "bellman ford, negative weight"),
                        ],
                    },
                    {
                        "name": "All-Pairs Shortest Paths",
                        "keywords": "floyd warshall, all pairs, transitive closure, dynamic programming, matrix",
                        "concepts": [
                            ("Floyd-Warshall", "All-pairs DP over intermediate vertices.", "floyd warshall, all pairs"),
                        ],
                    },
                ],
            },
        ],
    },
    {
        "code": "TOC",
        "name": "Theory of Computation",
        "sections": ["CS-6"],
        "color": "#ec4899",
        "description": "Automata, grammars, language classes, pumping lemma and computability.",
        "topics": [
            {
                "name": "Regular Expressions and Finite Automata",
                "section": "CS-6",
                "keywords": "regular expression, finite automata, dfa, nfa, epsilon nfa, minimization, regular language, closure",
                "subtopics": [
                    {
                        "name": "Finite Automata",
                        "keywords": "dfa, nfa, epsilon nfa, transition table, state diagram, dfa minimization, pumping lemma for regular languages",
                        "concepts": [
                            ("DFA and NFA", "Deterministic/non-deterministic automata.", "dfa, nfa, epsilon transition"),
                            ("Automata minimization", "Myhill-Nerode and DFA minimization.", "dfa minimization, myhill nerode, distinguishable"),
                            ("Regular pumping lemma", "Prove non-regularity.", "pumping lemma, regular language"),
                        ],
                    },
                    {
                        "name": "Regular Expressions",
                        "keywords": "regular expression, regex, kleene closure, union, concatenation, arden theorem, regular grammar",
                        "concepts": [
                            ("Regex to automata", "Thompson construction and Arden's theorem.", "regular expression, thompson, arden"),
                            ("Closure properties", "Union, intersection, complement and reversal.", "closure property, regular language"),
                        ],
                    },
                ],
            },
            {
                "name": "Context-Free Grammars and Pushdown Automata",
                "section": "CS-6",
                "keywords": "context free grammar, cfg, pushdown automata, pda, derivation, parse tree, ambiguity, chomsky normal form",
                "subtopics": [
                    {
                        "name": "Context-Free Grammars",
                        "keywords": "context free grammar, derivation, parse tree, ambiguity, left recursion, chomsky normal form, greibach normal form, simplification",
                        "concepts": [
                            ("Derivations and ambiguity", "Leftmost derivation and ambiguous grammars.", "derivation, parse tree, ambiguity"),
                            ("Normal forms", "CNF and GNF conversion.", "chomsky normal form, greibach normal form"),
                        ],
                    },
                    {
                        "name": "Pushdown Automata",
                        "keywords": "pushdown automata, pda, stack, acceptance by final state, acceptance by empty stack, deterministic pda, cfg to pda",
                        "concepts": [
                            ("PDA acceptance", "Final state vs empty stack.", "pda, final state, empty stack"),
                            ("CFG-PDA equivalence", "Convert grammars and automata.", "pda, cfg, equivalence"),
                        ],
                    },
                ],
            },
            {
                "name": "Regular and Context-Free Language Properties",
                "section": "CS-6",
                "keywords": "pumping lemma, cfl pumping lemma, closure properties, decision problems, membership, emptiness, cfl, regular language",
                "subtopics": [
                    {
                        "name": "Language Closures and Decision Problems",
                        "keywords": "closure properties, union, intersection, complement, decidable, membership, emptiness, finiteness, cfl pumping lemma",
                        "concepts": [
                            ("Closure properties", "Which operations preserve regularity/CFL.", "closure, union, intersection, complement"),
                            ("Decision procedures", "Membership, emptiness and finiteness.", "membership, emptiness, decidability"),
                            ("Pumping lemma", "Prove languages are not regular/CFL.", "pumping lemma, cfl pumping lemma"),
                        ],
                    },
                ],
            },
            {
                "name": "Turing Machines and Undecidability",
                "section": "CS-6",
                "keywords": "turing machine, undecidable, halting problem, reducibility, recursive, recursively enumerable, decidable, church turing",
                "subtopics": [
                    {
                        "name": "Turing Machines",
                        "keywords": "turing machine, tape, transition, configuration, multi tape, non deterministic turing machine, church turing thesis",
                        "concepts": [
                            ("TM model", "Configurations and transitions.", "turing machine, tape, configuration"),
                            ("Variants", "Multi-tape and non-deterministic TMs.", "multi tape, non deterministic turing machine"),
                        ],
                    },
                    {
                        "name": "Decidability and Reductions",
                        "keywords": "decidable, undecidable, halting problem, reduction, recursive, recursively enumerable, rice theorem, diagonalization",
                        "concepts": [
                            ("Decidable languages", "Recursive vs recursively enumerable.", "decidable, recursive, recursively enumerable"),
                            ("Reductions", "Mapping reductions and Rice's theorem.", "reduction, halting problem, rice theorem"),
                        ],
                    },
                ],
            },
        ],
    },
    {
        "code": "CD",
        "name": "Compiler Design",
        "sections": ["CS-7"],
        "color": "#14b8a6",
        "description": "Lexing, parsing, translation, runtime, IR, optimization and data flow.",
        "topics": [
            {
                "name": "Lexical Analysis",
                "section": "CS-7",
                "keywords": "lexical analysis, lexer, token, regular expression, dfa, nfa, symbol table, longest match",
                "subtopics": [
                    {
                        "name": "Tokenization",
                        "keywords": "token, lexeme, pattern, lexer, longest match, symbol table, regular expression, finite automata",
                        "concepts": [
                            ("Token specification", "Patterns, lexemes and tokens.", "token, lexeme, pattern"),
                            ("Lexer implementation", "DFA-based scanning and longest match.", "dfa, longest match, lexer"),
                        ],
                    },
                ],
            },
            {
                "name": "Parsing",
                "section": "CS-7",
                "keywords": "parsing, parser, ll, lr, slr, clr, lalr, first, follow, predictive parsing, shift reduce, ambiguous grammar",
                "subtopics": [
                    {
                        "name": "Top-Down Parsing",
                        "keywords": "ll(1), predictive parsing, recursive descent, first set, follow set, left factoring, left recursion",
                        "concepts": [
                            ("FIRST and FOLLOW", "Compute predictive parsing tables.", "first set, follow set, ll(1)"),
                            ("Grammar transformation", "Eliminate left recursion and factor.", "left recursion, left factoring"),
                        ],
                    },
                    {
                        "name": "Bottom-Up Parsing",
                        "keywords": "lr parsing, slr, lalr, clr, shift reduce, items, closure, goto, conflict, reduce reduce",
                        "concepts": [
                            ("LR items", "Item sets, closure and goto.", "lr item, closure, goto"),
                            ("Parser conflicts", "Shift-reduce and reduce-reduce.", "shift reduce conflict, reduce reduce conflict, slr, lalr"),
                        ],
                    },
                ],
            },
            {
                "name": "Syntax-Directed Translation",
                "section": "CS-7",
                "keywords": "syntax directed translation, attribute grammar, synthesized attribute, inherited attribute, semantic action, annotated parse tree",
                "subtopics": [
                    {
                        "name": "Attribute Grammars",
                        "keywords": "synthesized attribute, inherited attribute, semantic rule, annotated parse tree, s attributed, l attributed",
                        "concepts": [
                            ("Attributes", "Synthesized vs inherited evaluation.", "synthesized attribute, inherited attribute"),
                            ("Translation schemes", "Semantic actions in parsing.", "semantic action, translation scheme"),
                        ],
                    },
                ],
            },
            {
                "name": "Runtime Environments",
                "section": "CS-7",
                "keywords": "runtime environment, activation record, stack frame, heap, static allocation, dynamic allocation, parameter passing, scope",
                "subtopics": [
                    {
                        "name": "Activation Records and Storage",
                        "keywords": "activation record, stack frame, call stack, heap allocation, static allocation, dynamic allocation, scope, parameter passing",
                        "concepts": [
                            ("Activation records", "Stack frame layout and lifetime.", "activation record, stack frame"),
                            ("Storage allocation", "Static, stack and heap.", "static allocation, heap allocation, stack allocation"),
                        ],
                    },
                ],
            },
            {
                "name": "Intermediate Code Generation",
                "section": "CS-7",
                "keywords": "intermediate code, three address code, tac, quadruple, triple, dag, postfix, ir generation",
                "subtopics": [
                    {
                        "name": "Intermediate Representations",
                        "keywords": "three address code, quadruple, triple, indirect triple, dag, postfix, syntax tree, ir",
                        "concepts": [
                            ("Three-address code", "Generate TAC and quadruples.", "three address code, quadruple, triple"),
                            ("DAG representation", "Common subexpression sharing.", "dag, common subexpression"),
                        ],
                    },
                ],
            },
            {
                "name": "Local Optimization",
                "section": "CS-7",
                "keywords": "local optimization, peephole, constant folding, constant propagation, dead code elimination, common subexpression elimination, strength reduction",
                "subtopics": [
                    {
                        "name": "Optimization Techniques",
                        "keywords": "constant folding, constant propagation, dead code elimination, common subexpression elimination, strength reduction, peephole optimization, copy propagation",
                        "concepts": [
                            ("Local transformations", "Folding, propagation and dead code.", "constant folding, dead code, copy propagation"),
                            ("Common subexpression elimination", "Reuse equivalent expressions.", "common subexpression elimination, available expression"),
                        ],
                    },
                ],
            },
            {
                "name": "Data Flow Analysis",
                "section": "CS-7",
                "keywords": "data flow analysis, liveness, reaching definition, available expression, constant propagation, gen, kill, in, out, fixed point",
                "subtopics": [
                    {
                        "name": "Liveness and Reaching Definitions",
                        "keywords": "liveness analysis, live variable, reaching definition, gen, kill, in set, out set, data flow equation, fixed point",
                        "concepts": [
                            ("Liveness analysis", "Backward may-analysis for live variables.", "liveness, live variable, backward analysis"),
                            ("Reaching definitions", "Forward may-analysis.", "reaching definition, gen, kill"),
                        ],
                    },
                    {
                        "name": "Available Expressions",
                        "keywords": "available expression, forward analysis, must analysis, common subexpression elimination, data flow",
                        "concepts": [
                            ("Available expressions", "Forward must-analysis.", "available expression, must analysis"),
                        ],
                    },
                ],
            },
        ],
    },
    {
        "code": "OS",
        "name": "Operating Systems",
        "sections": ["CS-8"],
        "color": "#f97316",
        "description": "Processes, concurrency, scheduling, memory, virtual memory and file systems.",
        "topics": [
            {
                "name": "System Calls and Processes",
                "section": "CS-8",
                "keywords": "system call, process, fork, exec, wait, process control block, context switch, zombie, orphan",
                "subtopics": [
                    {
                        "name": "Processes and System Calls",
                        "keywords": "process, fork, exec, wait, exit, system call, process control block, context switch, zombie process, orphan process, pid",
                        "concepts": [
                            ("Process lifecycle", "Creation, states and termination.", "process state, fork, exec, wait"),
                            ("System calls", "Kernel interface and context switching.", "system call, context switch, kernel mode"),
                        ],
                    },
                ],
            },
            {
                "name": "Threads and IPC",
                "section": "CS-8",
                "keywords": "thread, multithreading, user level thread, kernel level thread, ipc, pipe, shared memory, message passing",
                "subtopics": [
                    {
                        "name": "Threads",
                        "keywords": "thread, user level thread, kernel level thread, thread control block, multithreading, concurrency, parallelism",
                        "concepts": [
                            ("Thread models", "User vs kernel threads.", "user level thread, kernel level thread"),
                            ("Threads vs processes", "Shared address space and overhead.", "thread, process, shared memory"),
                        ],
                    },
                    {
                        "name": "Inter-Process Communication",
                        "keywords": "ipc, pipe, named pipe, shared memory, message passing, semaphore, socket, producer consumer",
                        "concepts": [
                            ("Shared memory and pipes", "Data transfer between processes.", "shared memory, pipe, message passing"),
                            ("Synchronization primitives", "Semaphores and monitors.", "semaphore, monitor, mutex"),
                        ],
                    },
                ],
            },
            {
                "name": "Concurrency and Synchronization",
                "section": "CS-8",
                "keywords": "synchronization, critical section, mutual exclusion, semaphore, mutex, monitor, race condition, peterson, bakery",
                "subtopics": [
                    {
                        "name": "Critical Sections",
                        "keywords": "critical section, mutual exclusion, progress, bounded waiting, peterson algorithm, bakery algorithm, race condition",
                        "concepts": [
                            ("Critical section requirements", "Mutual exclusion, progress, bounded waiting.", "critical section, mutual exclusion, progress"),
                            ("Software solutions", "Peterson and bakery algorithms.", "peterson, bakery algorithm"),
                        ],
                    },
                    {
                        "name": "Semaphores and Monitors",
                        "keywords": "semaphore, binary semaphore, counting semaphore, wait, signal, mutex, monitor, condition variable",
                        "concepts": [
                            ("Semaphores", "P/V operations and usage patterns.", "semaphore, wait, signal"),
                            ("Monitors", "Condition variables and signaling.", "monitor, condition variable"),
                        ],
                    },
                ],
            },
            {
                "name": "Deadlocks",
                "section": "CS-8",
                "keywords": "deadlock, necessary conditions, resource allocation graph, banker algorithm, safety, detection, recovery, starvation",
                "subtopics": [
                    {
                        "name": "Deadlock Detection and Avoidance",
                        "keywords": "deadlock, mutual exclusion, hold and wait, no preemption, circular wait, resource allocation graph, banker algorithm, safe state, detection, recovery",
                        "concepts": [
                            ("Deadlock conditions", "Four necessary conditions.", "deadlock, circular wait, hold and wait"),
                            ("Banker's algorithm", "Safe-state and resource request checks.", "banker algorithm, safe state"),
                            ("Detection and recovery", "Wait-for graphs and preemption.", "resource allocation graph, deadlock detection, recovery"),
                        ],
                    },
                ],
            },
            {
                "name": "CPU and I/O Scheduling",
                "section": "CS-8",
                "keywords": "cpu scheduling, fcfs, sjf, srtf, round robin, priority scheduling, multilevel queue, turnaround time, waiting time, io scheduling",
                "subtopics": [
                    {
                        "name": "CPU Scheduling Algorithms",
                        "keywords": "fcfs, sjf, srtf, round robin, priority scheduling, multilevel feedback queue, preemptive, non preemptive, turnaround time, waiting time, response time, gantt chart",
                        "concepts": [
                            ("Scheduling metrics", "Turnaround, waiting and response time.", "turnaround time, waiting time, response time"),
                            ("Scheduling algorithms", "FCFS, SJF, SRTF, RR and priority.", "fcfs, sjf, srtf, round robin, priority"),
                        ],
                    },
                    {
                        "name": "I/O Scheduling",
                        "keywords": "io scheduling, fcfs, sstf, scan, c scan, look, disk scheduling, seek time, elevator",
                        "concepts": [
                            ("Disk scheduling", "Seek-time optimization.", "sstf, scan, c scan, look, seek time"),
                        ],
                    },
                ],
            },
            {
                "name": "Memory Management",
                "section": "CS-8",
                "keywords": "memory management, contiguous allocation, fragmentation, paging, segmentation, page table, tlb, physical address",
                "subtopics": [
                    {
                        "name": "Contiguous Allocation",
                        "keywords": "first fit, best fit, worst fit, next fit, fragmentation, compaction, partition, external fragmentation, internal fragmentation",
                        "concepts": [
                            ("Allocation strategies", "First/best/worst/next fit.", "first fit, best fit, worst fit, fragmentation"),
                            ("Fragmentation", "Internal vs external fragmentation.", "internal fragmentation, external fragmentation, compaction"),
                        ],
                    },
                    {
                        "name": "Paging and Segmentation",
                        "keywords": "paging, segmentation, page table, frame, page number, offset, tlb, multi level page table, inverted page table",
                        "concepts": [
                            ("Paging translation", "Page number and offset translation.", "paging, page table, frame, offset"),
                            ("TLB", "Translation lookaside buffer and hit time.", "tlb, translation, hit ratio"),
                            ("Segmentation", "Segments and protection.", "segmentation, segment table"),
                        ],
                    },
                ],
            },
            {
                "name": "Virtual Memory",
                "section": "CS-8",
                "keywords": "virtual memory, demand paging, page fault, page replacement, fifo, lru, optimal, thrashing, working set, belady",
                "subtopics": [
                    {
                        "name": "Demand Paging",
                        "keywords": "demand paging, page fault, page fault rate, effective access time, copy on write, swap",
                        "concepts": [
                            ("Page faults", "Handle faults and effective access time.", "page fault, effective access time"),
                        ],
                    },
                    {
                        "name": "Page Replacement",
                        "keywords": "page replacement, fifo, lru, optimal, clock, second chance, belady anomaly, reference string, hit ratio",
                        "concepts": [
                            ("Replacement algorithms", "FIFO, LRU, OPT and clock.", "fifo, lru, optimal, clock"),
                            ("Belady's anomaly", "More frames causing more faults.", "belady anomaly, reference string"),
                        ],
                    },
                    {
                        "name": "Thrashing and Working Set",
                        "keywords": "thrashing, working set, locality, degree of multiprogramming, page fault frequency, frame allocation",
                        "concepts": [
                            ("Thrashing", "Cause and control.", "thrashing, page fault frequency"),
                            ("Working set", "Locality-based frame allocation.", "working set, locality, frame allocation"),
                        ],
                    },
                ],
            },
            {
                "name": "File Systems",
                "section": "CS-8",
                "keywords": "file system, inode, directory, allocation, contiguous, linked, indexed, fat, journaling, disk block, free space",
                "subtopics": [
                    {
                        "name": "File Allocation and Directories",
                        "keywords": "inode, contiguous allocation, linked allocation, indexed allocation, fat, directory structure, hard link, symbolic link, free space management",
                        "concepts": [
                            ("Allocation methods", "Contiguous, linked and indexed.", "contiguous allocation, linked allocation, indexed allocation"),
                            ("Inodes and links", "Metadata and hard/symbolic links.", "inode, hard link, symbolic link"),
                        ],
                    },
                    {
                        "name": "Disk Layout and Reliability",
                        "keywords": "disk block, superblock, journaling, raid, file system consistency, mount, block size",
                        "concepts": [
                            ("Disk structures", "Superblocks, inode tables and block groups.", "superblock, inode table, block group"),
                            ("Reliability", "Journaling and consistency checks.", "journaling, consistency, raid"),
                        ],
                    },
                ],
            },
        ],
    },
    {
        "code": "DB",
        "name": "Databases",
        "sections": ["CS-9"],
        "color": "#3b82f6",
        "description": "ER modelling, relational theory, SQL, indexing, transactions and concurrency.",
        "topics": [
            {
                "name": "ER Model",
                "section": "CS-9",
                "keywords": "er model, entity, relationship, attribute, cardinality, participation, weak entity, generalization, er diagram",
                "subtopics": [
                    {
                        "name": "Entity-Relationship Design",
                        "keywords": "entity, relationship, attribute, cardinality ratio, participation constraint, weak entity, generalization, specialization, er diagram, ternary relationship",
                        "concepts": [
                            ("Entities and relationships", "Cardinality and participation.", "entity, relationship, cardinality, participation"),
                            ("ER to relational mapping", "Convert ER diagrams to tables.", "er mapping, weak entity, foreign key"),
                        ],
                    },
                ],
            },
            {
                "name": "Relational Model and Algebra",
                "section": "CS-9",
                "keywords": "relational model, relational algebra, selection, projection, join, division, union, difference, tuple calculus",
                "subtopics": [
                    {
                        "name": "Relational Algebra",
                        "keywords": "selection, projection, natural join, theta join, outer join, union, intersection, difference, division, rename, relational algebra",
                        "concepts": [
                            ("Basic operators", "Select, project, union and difference.", "selection, projection, union, difference"),
                            ("Joins", "Natural, theta and outer joins.", "natural join, theta join, outer join"),
                            ("Division", "Relational division and universal queries.", "division, relational algebra"),
                        ],
                    },
                    {
                        "name": "Tuple Relational Calculus",
                        "keywords": "tuple calculus, trc, domain calculus, predicate, quantified query, safe expression",
                        "concepts": [
                            ("TRC queries", "Express queries with tuple variables.", "tuple calculus, trc, predicate"),
                        ],
                    },
                ],
            },
            {
                "name": "SQL",
                "section": "CS-9",
                "keywords": "sql, select, join, group by, having, subquery, aggregate, view, trigger, constraint, null",
                "subtopics": [
                    {
                        "name": "SQL Queries",
                        "keywords": "sql, select, where, group by, having, order by, join, subquery, correlated subquery, aggregate, null, exists",
                        "concepts": [
                            ("Query formulation", "Joins, grouping and subqueries.", "sql, group by, having, subquery"),
                            ("NULL semantics", "Three-valued logic and outer joins.", "null, three valued logic"),
                        ],
                    },
                    {
                        "name": "SQL Schema and Constraints",
                        "keywords": "create table, primary key, foreign key, unique, check, not null, view, trigger, assertion",
                        "concepts": [
                            ("Constraints", "Keys and referential integrity.", "primary key, foreign key, check constraint"),
                            ("Views and triggers", "Derived relations and event handling.", "view, trigger, assertion"),
                        ],
                    },
                ],
            },
            {
                "name": "Integrity Constraints and Normal Forms",
                "section": "CS-9",
                "keywords": "functional dependency, normal form, 1nf, 2nf, 3nf, bcnf, closure, candidate key, decomposition, lossless, dependency preservation",
                "subtopics": [
                    {
                        "name": "Functional Dependencies",
                        "keywords": "functional dependency, armstrong axioms, closure, attribute closure, candidate key, superkey, minimal cover, multivalued dependency",
                        "concepts": [
                            ("FD closure", "Compute attribute closures and keys.", "functional dependency, closure, candidate key"),
                            ("Minimal cover", "Canonical cover computation.", "minimal cover, canonical cover"),
                        ],
                    },
                    {
                        "name": "Normalization",
                        "keywords": "normalization, 1nf, 2nf, 3nf, bcnf, 4nf, lossless join, dependency preservation, decomposition",
                        "concepts": [
                            ("Normal forms", "1NF through BCNF conditions.", "1nf, 2nf, 3nf, bcnf"),
                            ("Decomposition", "Lossless join and dependency preservation.", "lossless join, dependency preservation, decomposition"),
                        ],
                    },
                ],
            },
            {
                "name": "File Organization and Indexing",
                "section": "CS-9",
                "keywords": "file organization, heap file, sorted file, indexing, b tree, b+ tree, primary index, secondary index, dense index, sparse index",
                "subtopics": [
                    {
                        "name": "B and B+ Trees",
                        "keywords": "b tree, b+ tree, order, fanout, leaf node, internal node, split, merge, range query, index",
                        "concepts": [
                            ("B+ tree structure", "Order, occupancy and leaf links.", "b+ tree, leaf node, order"),
                            ("Index operations", "Search, insert, split and merge.", "b+ tree insertion, split, merge"),
                        ],
                    },
                    {
                        "name": "Indexing",
                        "keywords": "primary index, secondary index, dense index, sparse index, multilevel index, clustered, unclustered, hash index",
                        "concepts": [
                            ("Index types", "Dense/sparse and clustered/unclustered.", "dense index, sparse index, clustered index"),
                            ("Index performance", "I/O cost of lookups and range scans.", "index, io cost, range query"),
                        ],
                    },
                ],
            },
            {
                "name": "Transactions and Concurrency Control",
                "section": "CS-9",
                "keywords": "transaction, acid, serializability, conflict, precedence graph, lock, two phase locking, timestamp, deadlock, recovery, log",
                "subtopics": [
                    {
                        "name": "Transactions and Serializability",
                        "keywords": "transaction, acid, schedule, conflict serializability, view serializability, precedence graph, recoverable, cascadeless",
                        "concepts": [
                            ("ACID properties", "Atomicity, consistency, isolation, durability.", "acid, atomicity, isolation"),
                            ("Serializability", "Conflict and view serializability.", "conflict serializability, precedence graph, view serializability"),
                        ],
                    },
                    {
                        "name": "Concurrency Control",
                        "keywords": "two phase locking, 2pl, strict 2pl, shared lock, exclusive lock, timestamp ordering, optimistic concurrency, deadlock, wait die, wound wait",
                        "concepts": [
                            ("Locking protocols", "2PL, strict 2PL and lock compatibility.", "two phase locking, shared lock, exclusive lock"),
                            ("Timestamp ordering", "Timestamp-based concurrency.", "timestamp ordering, wait die, wound wait"),
                        ],
                    },
                    {
                        "name": "Recovery",
                        "keywords": "log, undo, redo, checkpoint, aries, write ahead log, shadow paging, recovery",
                        "concepts": [
                            ("Log-based recovery", "Undo/redo and checkpoints.", "write ahead log, undo, redo, checkpoint"),
                        ],
                    },
                ],
            },
        ],
    },
    {
        "code": "CN",
        "name": "Computer Networks",
        "sections": ["CS-10"],
        "color": "#22c55e",
        "description": "Layering, switching, link layer, routing, IPv4, TCP/UDP and applications.",
        "topics": [
            {
                "name": "Layering Principles",
                "section": "CS-10",
                "keywords": "layering, osi model, tcp/ip stack, encapsulation, protocol, service, interface, peer, header",
                "subtopics": [
                    {
                        "name": "Protocol Layering",
                        "keywords": "osi model, tcp/ip model, layer, encapsulation, decapsulation, protocol data unit, service, interface, peer entity",
                        "concepts": [
                            ("Layered architecture", "OSI and TCP/IP layers.", "osi, tcp/ip, layer"),
                            ("Encapsulation", "Headers and PDUs across layers.", "encapsulation, header, pdu"),
                        ],
                    },
                ],
            },
            {
                "name": "Switching and Performance Metrics",
                "section": "CS-10",
                "keywords": "circuit switching, packet switching, virtual circuit, datagram, performance, bandwidth, latency, throughput, delay, jitter",
                "subtopics": [
                    {
                        "name": "Switching Techniques",
                        "keywords": "circuit switching, packet switching, virtual circuit, datagram, store and forward, message switching",
                        "concepts": [
                            ("Circuit vs packet switching", "Resource reservation and delay.", "circuit switching, packet switching"),
                            ("Virtual circuits", "Connection-oriented forwarding.", "virtual circuit, datagram, store and forward"),
                        ],
                    },
                    {
                        "name": "Network Performance",
                        "keywords": "bandwidth, throughput, latency, propagation delay, transmission delay, queuing delay, processing delay, round trip time, jitter, bandwidth delay product",
                        "concepts": [
                            ("Delay components", "Transmission, propagation, queuing and processing.", "propagation delay, transmission delay, queuing delay"),
                            ("Throughput and utilization", "Bandwidth-delay product and pipeline.", "throughput, bandwidth delay product, utilization"),
                        ],
                    },
                ],
            },
            {
                "name": "Data Link Layer",
                "section": "CS-10",
                "keywords": "data link layer, error detection, crc, checksum, parity, mac, ethernet, csma/cd, sliding window, framing",
                "subtopics": [
                    {
                        "name": "Error Detection and Correction",
                        "keywords": "crc, cyclic redundancy check, parity, checksum, hamming code, error detection, error correction, framing, bit stuffing",
                        "concepts": [
                            ("Error detection", "Parity, checksum and CRC.", "crc, checksum, parity"),
                            ("Error correction", "Hamming distance and codes.", "hamming code, error correction"),
                            ("Framing", "Byte/bit stuffing and delimiters.", "framing, bit stuffing"),
                        ],
                    },
                    {
                        "name": "Medium Access Control",
                        "keywords": "mac, aloha, csma, csma/cd, csma/ca, collision, exponential backoff, token ring, polling, efficiency",
                        "concepts": [
                            ("Random access", "ALOHA and CSMA variants.", "aloha, csma, csma/cd, backoff"),
                            ("Controlled access", "Token passing and polling.", "token ring, polling"),
                            ("MAC efficiency", "Utilization and collision probability.", "efficiency, collision, utilization"),
                        ],
                    },
                    {
                        "name": "Ethernet",
                        "keywords": "ethernet, ieee 802.3, frame format, mac address, switch, hub, collision domain, broadcast domain, vlan",
                        "concepts": [
                            ("Ethernet frames", "Frame format and addressing.", "ethernet frame, mac address"),
                            ("Switching", "Learning switches and domains.", "switch, collision domain, broadcast domain"),
                        ],
                    },
                ],
            },
            {
                "name": "Routing",
                "section": "CS-10",
                "keywords": "routing, distance vector, link state, rip, ospf, bgp, bellman ford, dijkstra, routing table, count to infinity",
                "subtopics": [
                    {
                        "name": "Distance Vector Routing",
                        "keywords": "distance vector, rip, bellman ford, routing table, count to infinity, split horizon, poisoned reverse, triggered update",
                        "concepts": [
                            ("Distance-vector updates", "Neighbor exchange and convergence.", "distance vector, bellman ford, routing table"),
                            ("Count-to-infinity", "Loop prevention mechanisms.", "count to infinity, split horizon, poisoned reverse"),
                        ],
                    },
                    {
                        "name": "Link State Routing",
                        "keywords": "link state, ospf, dijkstra, link state advertisement, flooding, shortest path first, topology database",
                        "concepts": [
                            ("Link-state operation", "LSA flooding and SPF.", "link state, lsa, dijkstra"),
                        ],
                    },
                ],
            },
            {
                "name": "IPv4",
                "section": "CS-10",
                "keywords": "ipv4, fragmentation, cidr, subnetting, nat, ip address, subnet mask, mtu, header, arp, icmp",
                "subtopics": [
                    {
                        "name": "IPv4 Addressing and Subnetting",
                        "keywords": "ipv4, ip address, classful, cidr, subnet mask, prefix, subnetting, supernetting, network address, broadcast address, host range",
                        "concepts": [
                            ("Subnetting", "Network/host split and usable hosts.", "subnetting, subnet mask, host range"),
                            ("CIDR", "Prefix aggregation and longest prefix match.", "cidr, prefix, longest prefix match"),
                        ],
                    },
                    {
                        "name": "Fragmentation",
                        "keywords": "fragmentation, mtu, fragment offset, more fragments, identification, reassembly, df flag, mf flag",
                        "concepts": [
                            ("IP fragmentation", "Fragment offset and payload sizing.", "fragmentation, mtu, fragment offset"),
                            ("Reassembly", "Identification and flags.", "reassembly, more fragments, df flag"),
                        ],
                    },
                    {
                        "name": "NAT and Supporting Protocols",
                        "keywords": "nat, network address translation, pat, port forwarding, arp, icmp, dhcp, private address",
                        "concepts": [
                            ("NAT", "Address/port translation tables.", "nat, pat, port forwarding"),
                            ("Supporting protocols", "ARP, ICMP and DHCP.", "arp, icmp, dhcp"),
                        ],
                    },
                ],
            },
            {
                "name": "TCP",
                "section": "CS-10",
                "keywords": "tcp, transmission control protocol, three way handshake, flow control, congestion control, slow start, congestion avoidance, retransmission, socket api",
                "subtopics": [
                    {
                        "name": "TCP Fundamentals",
                        "keywords": "tcp, three way handshake, sequence number, acknowledgement, header, connection teardown, retransmission timeout, rtt estimation, karn algorithm",
                        "concepts": [
                            ("Connection management", "Handshake, teardown and states.", "three way handshake, sequence number, teardown"),
                            ("Reliable delivery", "ACKs, timers and retransmission.", "retransmission, rtt, karn algorithm"),
                        ],
                    },
                    {
                        "name": "TCP Flow Control",
                        "keywords": "flow control, receive window, advertised window, sliding window, window scaling, zero window, silly window syndrome",
                        "concepts": [
                            ("Sliding window", "Sender/receiver window limits.", "sliding window, receive window, advertised window"),
                        ],
                    },
                    {
                        "name": "TCP Congestion Control",
                        "keywords": "congestion control, slow start, congestion avoidance, congestion window, threshold, fast retransmit, fast recovery, aimd, timeout",
                        "concepts": [
                            ("Slow start", "Exponential growth of cwnd.", "slow start, congestion window, threshold"),
                            ("Congestion avoidance", "AIMD and additive increase.", "congestion avoidance, aimd"),
                            ("Fast retransmit/recovery", "Three duplicate ACKs and recovery.", "fast retransmit, fast recovery, duplicate ack"),
                        ],
                    },
                    {
                        "name": "Socket API",
                        "keywords": "socket api, socket, bind, listen, accept, connect, send, recv, port, client server, listen backlog",
                        "concepts": [
                            ("Socket calls", "Server/client call sequence.", "socket, bind, listen, accept, connect"),
                        ],
                    },
                ],
            },
            {
                "name": "UDP",
                "section": "CS-10",
                "keywords": "udp, user datagram protocol, connectionless, datagram, checksum, port, unreliable",
                "subtopics": [
                    {
                        "name": "UDP Operation",
                        "keywords": "udp, connectionless, datagram, checksum, port number, no retransmission, header",
                        "concepts": [
                            ("UDP characteristics", "Connectionless, unreliable datagrams.", "udp, connectionless, datagram"),
                            ("UDP checksum", "Pseudo-header checksum.", "udp checksum, pseudo header"),
                        ],
                    },
                ],
            },
            {
                "name": "Application Layer",
                "section": "CS-10",
                "keywords": "application layer, dns, http, https, url, web cache, cookie, name resolution, persistent connection",
                "subtopics": [
                    {
                        "name": "DNS",
                        "keywords": "dns, domain name system, resolver, root server, tld, authoritative, recursive query, iterative query, caching, resource record",
                        "concepts": [
                            ("Name resolution", "Recursive vs iterative queries.", "dns, recursive query, iterative query"),
                            ("DNS records", "Resource records and caching.", "resource record, ttl, caching"),
                        ],
                    },
                    {
                        "name": "HTTP",
                        "keywords": "http, https, request, response, header, status code, persistent connection, pipelining, cookie, web cache, proxy",
                        "concepts": [
                            ("HTTP messages", "Methods, status codes and headers.", "http request, status code, header"),
                            ("HTTP performance", "Persistent connections and caching.", "persistent connection, pipelining, web cache, cookie"),
                        ],
                    },
                ],
            },
        ],
    },
]
