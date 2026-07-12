"""Core Malaysian statutory calculation modules.

Each contribution has its own focused module — :mod:`kwsp` (EPF), :mod:`socso`,
:mod:`eis` and :mod:`pcb` — sharing the rate configuration in :mod:`rates`.
Every module exposes ``contribution``/``estimate`` (the numbers) and ``explain``
(a plain-English derivation used by the reviewer dashboard).
"""
