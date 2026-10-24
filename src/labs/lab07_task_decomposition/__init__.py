"""Lab 07 - Reasoning Guidance & Task Decomposition. See README.md (Turkish).

Rule followed throughout this package (spec Section 11 LAB 07): hidden reasoning text is
never requested (`include_reasoning=False`), never captured by `GroqClientAdapter`
(`CompletionResult.content` only ever holds `message.content`), and therefore never stored
or evaluated. There is no code path in this lab that reads a `reasoning` field at all.
"""
