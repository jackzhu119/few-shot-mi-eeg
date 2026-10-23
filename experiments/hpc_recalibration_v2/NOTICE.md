# Scope and attribution

Original project code is covered by the repository's MIT license. Original
documentation and derived summaries retain the repository's scoped CC BY 4.0
policy. See the repository LICENSE and LICENSES files for the complete terms.

The private input bundle contains a processed subset of Kumar2024, NEMAR
nm000177 version 1.0.5, credited to the original investigators. The source
dataset is distributed under CC BY 4.0; project authorship does not replace
that attribution. Original article: https://doi.org/10.1093/pnasnexus/pgae076;
correction: https://doi.org/10.1093/pnasnexus/pgae137. Window provenance and
trial exclusions are carried in the separate input manifest. Five-second
cue-aligned samples are not asserted to contain continuous motor imagery.

NumPy, PyTorch and the existing CUDA runtime retain their respective licenses.
The code package does not redistribute those dependencies, EEG, model weights,
tokens or third-party model implementations. The pure PyTorch EEGNet-style
architecture is an explicitly separate implementation, not a loader for the
historical Braindecode checkpoints. EEGNet reference:
https://doi.org/10.1088/1741-2552/aace8c.

No BNCI or OpenBMI raw/derived signals are included. Their licenses and split
proposals are documented separately; this package makes no claim that an
external validation has been run.
