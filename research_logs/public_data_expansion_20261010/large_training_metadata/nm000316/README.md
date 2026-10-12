[![DOI](https://img.shields.io/badge/DOI-10.82901%2Fnemar.nm000316-blue)](https://doi.org/10.82901/nemar.nm000316)

IMUMIA2026
==========

Multi-paradigm motor-imagery EEG dataset (IMU-MI_A) [1]_.

Dataset Overview
----------------
  Code: IMUMIA2026
  Paradigm: imagery
  DOI: 10.5281/zenodo.20421767
  Subjects: 5
  Sessions per subject: 1
  Events: left_hand=1, right_hand=2, left_foot=3, right_foot=4, left_thumb=5, right_thumb=6, left_index=7, right_index=8, left_pinch=9, right_pinch=10
  Trial interval: [0, 4] s
  Runs per session: 5
  File format: Curry

Acquisition
-----------
  Sampling rate: 1000.0 Hz
  Number of channels: 69
  Channel types: eeg=64, eog=2, ecg=1, emg=1, misc=1
  Channel names: FP1, FPZ, FP2, AF3, AF4, F7, F5, F3, F1, FZ, F2, F4, F6, F8, FT7, FC5, FC3, FC1, FCZ, FC2, FC4, FC6, FT8, T7, C5, C3, C1, CZ, C2, C4, C6, T8, M1, TP7, CP5, CP3, CP1, CPZ, CP2, CP4, CP6, TP8, M2, P7, P5, P3, P1, PZ, P2, P4, P6, P8, PO7, PO5, PO3, POZ, PO4, PO6, PO8, CB1, O1, OZ, O2, CB2
  Montage: standard_1020
  Hardware: Neuroscan SynAmps (64-channel Quik-Cap)
  Reference: Cz
  Ground: forehead
  Sensor type: Ag/AgCl
  Line frequency: 50.0 Hz
  Impedance threshold: 10.0 kOhm
  Electrode type: passive
  Auxiliary channels: EOG (2 ch, HEO, VEO), EMG (1 ch), ECG

Participants
------------
  Number of subjects: 5
  Health status: healthy

Experimental Protocol
---------------------
  Paradigm: imagery
  Number of classes: 10
  Class labels: left_hand, right_hand, left_foot, right_foot, left_thumb, right_thumb, left_index, right_index, left_pinch, right_pinch
  Trial duration: 6.0 s
  Study design: Five motor-imagery tasks (left/right hand, foot, thumb, index finger and index-thumb pinch), each recorded under a Classic Arrow paradigm and a Cue-Execution dual-stage paradigm.
  Stimulus type: visual
  Stimulus modalities: visual
  Synchronicity: cue-based
  Mode: offline
  Instructions: Perform the cued left- or right-side motor imagery of the task's body part following the arrow direction.

HED Event Annotations
---------------------
  Schema: HED 8.4.0 | Browse: https://www.hedtags.org/hed-schema-browser

  left_hand
    ├─ Sensory-event, Experimental-stimulus, Visual-presentation
    └─ Agent-action
       └─ Imagine
          ├─ Move
          └─ Left, Hand

  right_hand
    ├─ Sensory-event, Experimental-stimulus, Visual-presentation
    └─ Agent-action
       └─ Imagine
          ├─ Move
          └─ Right, Hand

  left_foot
    ├─ Sensory-event
    └─ Label/left_foot

  right_foot
    ├─ Sensory-event
    └─ Label/right_foot

  left_thumb
    ├─ Sensory-event
    └─ Label/left_thumb

  right_thumb
    ├─ Sensory-event
    └─ Label/right_thumb

  left_index
    ├─ Sensory-event
    └─ Label/left_index

  right_index
    ├─ Sensory-event
    └─ Label/right_index

  left_pinch
    ├─ Sensory-event
    └─ Label/left_pinch

  right_pinch
    ├─ Sensory-event
    └─ Label/right_pinch

Paradigm-Specific Parameters
----------------------------
  Detected paradigm: motor_imagery
  Imagery tasks: left_hand, right_hand, left_foot, right_foot, left_thumb, right_thumb, left_index, right_index, left_pinch, right_pinch
  Imagery duration: 4.0 s

Data Structure
--------------
  Blocks per session: 5
  Trials context: Single session with five runs (one motor-imagery task each). Only the Classic Arrow cues (12 trials per side and task) are labelled by default; the dual-stage paradigm markers are kept in the annotations.

Preprocessing
-------------
  Data state: raw
  Preprocessing applied: False

Tags
----
  Pathology: healthy
  Modality: motor
  Type: Motor Imagery

Documentation
-------------
  Description: Human motor-imagery EEG covering diverse cognitive states: five body-part tasks (hand, foot, thumb, index finger, pinch) under two paradigms, 64-channel Neuroscan at 1000 Hz. Public five-subject sample of a 244-participant dataset.
  DOI: 10.5281/zenodo.20421767
  License: CC-BY-4.0
  Investigators: Jianxiu Li, Changming Wang, Chao Chen
  Institution: Inner Mongolia University
  Address: Inner Mongolia, China
  Country: CN
  Repository: Zenodo
  Data URL: https://doi.org/10.5281/zenodo.20421767
  Publication year: 2026
  Keywords: EEG, motor imagery, BCI, fine motor imagery

References
----------
Li, J., Wang, C., and Chen, C. (2026). A Human Motor Imagery EEG Dataset Covering Diverse Cognitive States and Neural Response Patterns. Zenodo. DOI: https://doi.org/10.5281/zenodo.20421767

Notes

The numeric event code to left/right assignment follows the authors' documented condition order (the "Left ... MI" condition is listed before the "Right ... MI" condition in every ``task-Task*_events.json``); the archive ships no explicit trigger code book. Users are advised to verify laterality against the EMG/EOG channels before publication.

.. versionadded:: 1.8.0
Appelhoff, S., Sanderson, M., Brooks, T., Vliet, M., Quentin, R., Holdgraf, C., Chaumon, M., Mikulan, E., Tavabi, K., Hochenberger, R., Welke, D., Brunner, C., Rockhill, A., Larson, E., Gramfort, A. and Jas, M. (2019). MNE-BIDS: Organizing electrophysiological data into the BIDS format and facilitating their analysis. Journal of Open Source Software 4: (1896). https://doi.org/10.21105/joss.01896

Pernet, C. R., Appelhoff, S., Gorgolewski, K. J., Flandin, G., Phillips, C., Delorme, A., Oostenveld, R. (2019). EEG-BIDS, an extension to the brain imaging data structure for electroencephalography. Scientific Data, 6, 103. https://doi.org/10.1038/s41597-019-0104-8

---
Generated by MOABB 1.8.0dev0 (Mother of All BCI Benchmarks)
https://github.com/NeuroTechX/moabb

Ethics
------
Ethics approval: the data analysed in this deposit were collected under the
ethics approval obtained by the original investigators and reported in the
primary publication cited above (see References/Documentation sections of
this README). Participants gave informed consent in the source study. No
new human-subject data were collected during this BIDS re-release; this
NEMAR record only reformats the published source data into BIDS via MOABB.
Please consult the primary publication for the exact IRB/ethics committee
reference.
