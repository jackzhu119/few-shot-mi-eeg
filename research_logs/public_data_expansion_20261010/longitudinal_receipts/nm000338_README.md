[![DOI](https://img.shields.io/badge/DOI-10.82901%2Fnemar.nm000338-blue)](https://doi.org/10.82901/nemar.nm000338)

Lee2019-MI
==========

BMI/OpenBMI dataset for MI.

Dataset Overview
----------------
  Code: Lee2019-MI
  Paradigm: imagery
  DOI: 10.5524/100542
  Subjects: 54
  Sessions per subject: 2
  Events: left_hand=2, right_hand=1
  Trial interval: [0.0, 4.0] s
  File format: MAT

Acquisition
-----------
  Sampling rate: 1000.0 Hz
  Number of channels: 62
  Channel types: eeg=62, emg=4
  Channel names: AF3, AF4, AF7, AF8, C1, C2, C3, C4, C5, C6, CP1, CP2, CP3, CP4, CP5, CP6, CPz, Cz, EMG1, EMG2, EMG3, EMG4, F10, F3, F4, F7, F8, F9, FC1, FC2, FC3, FC4, FC5, FC6, FT10, FT9, FTT10h, FTT9h, Fp1, Fp2, Fz, O1, O2, Oz, P1, P2, P3, P4, P7, P8, PO10, PO3, PO4, PO9, POz, Pz, T7, T8, TP10, TP7, TP8, TP9, TPP10h, TPP8h, TPP9h, TTP7h
  Montage: standard_1005
  Hardware: BrainAmp
  Reference: nasion
  Ground: AFz
  Sensor type: Ag/AgCl
  Line frequency: 60.0 Hz
  Impedance threshold: 10.0 kOhm
  Auxiliary channels: EMG (4 ch)

Participants
------------
  Number of subjects: 54
  Health status: healthy
  Age: min=24, max=35
  Gender distribution: female=25, male=29
  Handedness: {'right': 50, 'left': 2, 'ambidexter': 2}
  BCI experience: mixed

Experimental Protocol
---------------------
  Paradigm: imagery
  Number of classes: 2
  Class labels: left_hand, right_hand
  Trial duration: 4.0 s
  Tasks: MI
  Study design: Binary-class motor imagery (left/right hand grasping). Two sessions on different days, each with offline training and online test phases of 100 trials each.
  Feedback type: visual
  Stimulus type: arrow
  Stimulus modalities: visual
  Primary modality: visual
  Synchronicity: synchronous
  Mode: both
  Training/test split: True
  Instructions: Subjects performed the imagery task of grasping with the appropriate hand for 4 s when the right or left arrow appeared as a visual cue. First 3 s of each trial began with a black fixation cross to prepare subjects for the MI task. After each task, the screen remained blank for 6 s (± 1.5 s).

HED Event Annotations
---------------------
  Schema: HED 8.4.0 | Browse: https://www.hedtags.org/hed-schema-browser

  left_hand
    ├─ Sensory-event
    │  ├─ Experimental-stimulus
    │  ├─ Visual-presentation
    │  └─ Leftward, Arrow
    └─ Agent-action
       └─ Imagine
          ├─ Move
          └─ Left, Hand

  right_hand
    ├─ Sensory-event
    │  ├─ Experimental-stimulus
    │  ├─ Visual-presentation
    │  └─ Rightward, Arrow
    └─ Agent-action
       └─ Imagine
          ├─ Move
          └─ Right, Hand

Paradigm-Specific Parameters
----------------------------
  Detected paradigm: motor_imagery
  Imagery tasks: left_hand, right_hand
  Cue duration: 3.0 s
  Imagery duration: 4.0 s

Data Structure
--------------
  Trials: 200
  Trials per class: left_hand=100, right_hand=100
  Trials context: 100 trials per session per phase (50 per class per phase). Training: 50 left + 50 right. Test: 50 left + 50 right. Total per session: 200.

Preprocessing
-------------
  Data state: raw
  Preprocessing applied: False

Signal Processing
-----------------
  Classifiers: CSP+LDA, CSSP, FBCSP, BSSFO
  Feature extraction: CSP, CSSP, FBCSP, BSSFO, log-variance
  Frequency bands: mu=[8.0, 12.0] Hz; analyzed=[8.0, 30.0] Hz
  Spatial filters: CSP, CSSP, FBCSP, BSSFO

Cross-Validation
----------------
  Method: train-test split
  Evaluation type: within_session, cross_session

Performance (Original Study)
----------------------------
  Accuracy: 71.1%
  Accuracy Std: 0.15
  Illiteracy Rate: 53.7
  Session1 Accuracy: 70.0
  Session2 Accuracy: 72.2

BCI Application
---------------
  Applications: motor_control
  Environment: laboratory
  Online feedback: True

Tags
----
  Pathology: Healthy
  Modality: Motor
  Type: Research

Documentation
-------------
  Description: EEG dataset and OpenBMI toolbox for three BCI paradigms: an investigation into BCI illiteracy. Includes MI, ERP, and SSVEP paradigms with a large number of subjects over multiple sessions.
  DOI: 10.1093/gigascience/giz002
  License: GPL-3.0
  Investigators: Min-Ho Lee, O-Yeon Kwon, Yong-Jeong Kim, Hong-Kyung Kim, Young-Eun Lee, John Williamson, Siamac Fazli, Seong-Whan Lee
  Senior author: Seong-Whan Lee
  Contact: sw.lee@korea.ac.kr
  Institution: Korea University
  Department: Department of Brain and Cognitive Engineering
  Address: 145 Anam-ro, Seongbuk-gu, Seoul, 02841, Korea
  Country: KR
  Repository: GigaDB
  Publication year: 2019
  How to acknowledge: This is an Open Access article distributed under the terms of the Creative Commons Attribution License (http://creativecommons.org/licenses/by/4.0/), which permits unrestricted reuse, distribution, and reproduction in any medium, provided the original work is properly cited.
  Keywords: EEG datasets, brain-computer interface, event-related potential, steady-state visually evoked potential, motor-imagery, OpenBMI toolbox, BCI illiteracy

Abstract
--------
Electroencephalography (EEG)-based brain-computer interface (BCI) systems are mainly divided into three major paradigms: motor imagery (MI), event-related potential (ERP), and steady-state visually evoked potential (SSVEP). Here, we present a BCI dataset that includes the three major BCI paradigms with a large number of subjects over multiple sessions. In addition, information about the psychological and physiological conditions of BCI users was obtained using a questionnaire, and task-unrelated parameters such as resting state, artifacts, and electromyography of both arms were also recorded. We evaluated the decoding accuracies for the individual paradigms and determined performance variations across both subjects and sessions. Furthermore, we looked for more general, severe cases of BCI illiteracy than have been previously reported in the literature. Average decoding accuracies across all subjects and sessions were 71.1% (± 0.15), 96.7% (± 0.05), and 95.1% (± 0.09), and rates of BCI illiteracy were 53.7%, 11.1%, and 10.2% for MI, ERP, and SSVEP, respectively. Compared to the ERP and SSVEP paradigms, the MI paradigm exhibited large performance variations between both subjects and sessions. Furthermore, we found that 27.8% (15 out of 54) of users were universally BCI literate, i.e., they were able to proficiently perform all three paradigms. Interestingly, we found no universally illiterate BCI user, i.e., all participants were able to control at least one type of BCI system.

Methodology
-----------
Experimental procedure: 54 healthy subjects participated in two sessions on different days. Each session consisted of three BCI paradigms performed sequentially: ERP speller (36 symbols, row-column presentation with face stimuli), MI task (binary left/right hand imagery), and SSVEP (four target frequencies: 5.45, 6.67, 8.57, 12 Hz). Each paradigm had offline training and online test phases. EEG recorded at 1000 Hz with 62 Ag/AgCl electrodes using BrainAmp amplifier, nose-referenced, grounded to AFz. Impedance maintained below 10 kOhm. Subjects seated 60 cm from 21-inch LCD monitor. Questionnaires collected demographic, physiological, and psychological data. Artifact data (eye blinking, eye movements, teeth clenching, arm flexing) and resting state EEG also recorded. Total experiment duration: ~205 minutes per session.

References
----------
Lee, M. H., Kwon, O. Y., Kim, Y. J., Kim, H. K., Lee, Y. E., Williamson, J., … Lee, S. W. (2019). EEG dataset and OpenBMI toolbox for three BCI paradigms: An investigation into BCI illiteracy. GigaScience, 8(5), 1–16. https://doi.org/10.1093/gigascience/giz002
Appelhoff, S., Sanderson, M., Brooks, T., Vliet, M., Quentin, R., Holdgraf, C., Chaumon, M., Mikulan, E., Tavabi, K., Hochenberger, R., Welke, D., Brunner, C., Rockhill, A., Larson, E., Gramfort, A. and Jas, M. (2019). MNE-BIDS: Organizing electrophysiological data into the BIDS format and facilitating their analysis. Journal of Open Source Software 4: (1896). https://doi.org/10.21105/joss.01896

Pernet, C. R., Appelhoff, S., Gorgolewski, K. J., Flandin, G., Phillips, C., Delorme, A., Oostenveld, R. (2019). EEG-BIDS, an extension to the brain imaging data structure for electroencephalography. Scientific Data, 6, 103. https://doi.org/10.1038/s41597-019-0104-8

---
Generated by MOABB 1.5.0 (Mother of All BCI Benchmarks)
https://github.com/NeuroTechX/moabb
