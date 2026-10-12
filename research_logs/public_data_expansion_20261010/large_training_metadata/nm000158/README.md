[![DOI](https://img.shields.io/badge/DOI-10.82901%2Fnemar.nm000158-blue)](https://doi.org/10.82901/nemar.nm000158)

# Dataset [1]_ from the study on motor imagery [2]_

Dataset [1]_ from the study on motor imagery [2]_.

## Dataset Overview

- **Code**: Liu2024
- **Paradigm**: imagery
- **DOI**: 10.1038/s41597-023-02787-8
- **Subjects**: 50
- **Sessions per subject**: 1
- **Events**: left_hand=1, right_hand=2
- **Trial interval**: (0, 4) s
- **File format**: MAT and EDF
- **Data preprocessed**: True
- **Contributing labs**: Xuanwu Hospital Capital Medical University

## Acquisition

- **Sampling rate**: 500.0 Hz
- **Number of channels**: 29
- **Channel types**: eeg=29, eog=2
- **Channel names**: C3, C4, CP3, CP4, Cz, F3, F4, F7, F8, FC3, FC4, FCz, FP1, FP2, FT7, FT8, Fz, HEOL, O1, O2, Oz, P3, P4, Pz, T3, T4, T5, T6, TP7, TP8, VEOR
- **Montage**: 10-10
- **Hardware**: ZhenTec NT1 wireless multichannel EEG acquisition system
- **Reference**: CPz
- **Ground**: FPz
- **Sensor type**: semi-dry Ag/AgCl
- **Line frequency**: 50.0 Hz
- **Impedance threshold**: 20 kOhm
- **Cap manufacturer**: Xi'an ZhenTec Intelligence Technology Co., Ltd.
- **Cap model**: ZhenTec NT1
- **Electrode type**: semi-dry
- **Electrode material**: Ag/AgCl semi-dry electrodes based on highly absorbable porous sponges dampened with 3% NaCl solution
- **Auxiliary channels**: EOG (2 ch, horizontal, vertical)

## Participants

- **Number of subjects**: 50
- **Health status**: acute stroke patients
- **Clinical population**: acute stroke patients (1-30 days post-stroke)
- **Age**: mean=56.7, std=10.57, min=31.0, max=77.0
- **Gender distribution**: male=39, female=11

## Experimental Protocol

- **Paradigm**: imagery
- **Number of classes**: 2
- **Class labels**: left_hand, right_hand
- **Trial duration**: 8.0 s
- **Trials per class**: left_hand=20, right_hand=20
- **Study design**: Imagining grasping a spherical object with left or right hand while watching a video of gripping motion. Each trial: instruction stage (prompt), MI stage (4s video-guided imagery), break stage (rest).
- **Feedback type**: none
- **Stimulus type**: video and audio
- **Stimulus modalities**: visual, audio
- **Synchronicity**: cue-based
- **Mode**: offline
- **Training/test split**: True
- **Instructions**: Subject sat approximately 80 cm from computer screen. Computer played audio instructions. Patients imagined grasping spherical object with prompted hand during 4s video playback.

## HED Event Annotations

Schema: HED 8.4.0 | Browse: https://www.hedtags.org/hed-schema-browser

```
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

```
## Paradigm-Specific Parameters

- **Detected paradigm**: motor_imagery
- **Imagery tasks**: left_hand, right_hand
- **Cue duration**: 2.0 s
- **Imagery duration**: 4.0 s

## Data Structure

- **Trials**: 40
- **Trials per class**: left_hand=20, right_hand=20
- **Trials context**: 40 trials per subject total (20 left-hand, 20 right-hand), alternating. Each trial: 8s total (instruction + 4s MI + break). Training/test split: 60%/40%.

## Preprocessing

- **Data state**: preprocessed
- **Preprocessing applied**: True
- **Steps**: baseline removal (mean removal method), FIR filtering (0.5-40 Hz)
- **Highpass filter**: 0.5 Hz
- **Lowpass filter**: 40.0 Hz
- **Bandpass filter**: [0.5, 40.0]
- **Filter type**: FIR
- **Epoch window**: [0.0, 8.0]
- **Notes**: Preprocessed with EEGLAB toolbox in MATLAB R2019b. Filtered data split into trials x channels x time-samples format by marker '1'. Some motion artifacts present in subjects 4, 5, 13, 14, 18, 24, 28, 33, 42, 43, 47, 48, 49.

## Signal Processing

- **Classifiers**: CSP+LDA, FBCSP+SVM, TSLDA+DGFMDRM, TWFB+DGFMDM
- **Feature extraction**: CSP, FBCSP, ERD/ERS, Riemannian geometry (SCMs on SPD manifolds), Tangent Space, Time-Frequency (Morlet wavelet), TWFB (Time Window Filter Bank)
- **Frequency bands**: alpha=[8.0, 15.0] Hz; beta=[15.0, 30.0] Hz; analyzed=[8.0, 30.0] Hz
- **Spatial filters**: CSP, FBCSP, Discriminant Geodesic Filtering

## Cross-Validation

- **Method**: 10-fold cross-validation
- **Folds**: 10
- **Evaluation type**: within_subject

## Performance (Original Study)

- **Csp+Lda Accuracy**: 55.57
- **Fbcsp+Svm Accuracy**: 57.57
- **Tslda+Dgfmdrm Accuracy**: 61.2
- **Twfb+Dgfmdm Accuracy**: 72.21
- **Twfb+Dgfmdm Kappa**: 0.4442
- **Twfb+Dgfmdm Precision**: 0.7543
- **Twfb+Dgfmdm Sensitivity**: 0.7845

## BCI Application

- **Applications**: rehabilitation
- **Environment**: hospital
- **Online feedback**: False

## Tags

- **Pathology**: Stroke
- **Modality**: Motor
- **Type**: Motor Imagery

## Documentation

- **Description**: EEG motor imagery dataset from 50 acute stroke patients performing left- and right-handed hand-grip imagination tasks. First open dataset addressing left- and right-handed motor imagery in acute stroke patients.
- **DOI**: 10.1038/s41597-023-02787-8
- **License**: CC-BY-4.0
- **Investigators**: Haijie Liu, Penghu Wei, Haochong Wang, Xiaodong Lv, Wei Duan, Meijie Li, Yan Zhao, Qingmei Wang, Xinyuan Chen, Gaige Shi, Bo Han, Junwei Hao
- **Senior author**: Junwei Hao
- **Contact**: haojunwei@vip.163.com
- **Institution**: Xuanwu Hospital Capital Medical University
- **Department**: Department of Neurology
- **Address**: Beijing, 100053, China
- **Country**: CN
- **Repository**: Figshare
- **Data URL**: https://doi.org/10.6084/m9.figshare.21679035.v5
- **Publication year**: 2024
- **Funding**: National Natural Science Foundation of China (grant nos. 82090043 and 81825008)
- **Ethics approval**: Ethics Committee of Xuanwu Hospital of Capital Medical University (No. 2021-236)
- **Keywords**: motor imagery, BCI, brain-computer interface, stroke patients, EEG, rehabilitation, acute stroke, hand-grip imagery, databases, scientific data

## Abstract

The brain-computer interface (BCI) is a technology that involves direct communication with parts of the brain and has evolved rapidly in recent years; it has begun to be used in clinical practice, such as for patient rehabilitation. Patient electroencephalography (EEG) datasets are critical for algorithm optimization and clinical applications of BCIs but are rare at present. We collected data from 50 acute stroke patients with wireless portable saline EEG devices during the performance of two tasks: 1) imagining right-handed movements and 2) imagining left-handed movements. The dataset consists of four types of data: 1) the motor imagery instructions, 2) raw recording data, 3) pre-processed data after removing artefacts and other manipulations, and 4) patient characteristics. This is the first open dataset to address left- and right-handed motor imagery in acute stroke patients.

## Methodology

50 acute stroke patients (1-30 days post-stroke) performed 40 trials of hand-grip motor imagery (20 left, 20 right). Each 8s trial included instruction, 4s video-guided imagery, and rest phases. EEG recorded with ZhenTec NT1 wireless system (29 EEG + 2 EOG channels) at 500 Hz. Data organized in EEG-BIDS format with raw (.mat) and preprocessed (.edf) versions. Clinical assessments: NIHSS (mean=4.16, SD=2.85), MBI (mean=70.94, SD=18.22), mRS (mean=2.66, SD=1.44). 23 patients right hemiplegia, 27 left hemiplegia.

## References

Liu, Haijie; Lv, Xiaodong (2022). EEG datasets of stroke patients. figshare. Dataset. DOI: https://doi.org/10.6084/m9.figshare.21679035.v5

Liu, Haijie, Wei, P., Wang, H. et al. An EEG motor imagery dataset for brain computer interface in acute stroke patients. Sci Data 11, 131 (2024). DOI: https://doi.org/10.1038/s41597-023-02787-8

Notes

To add the break and instruction events, set the `break_events` and `instr_events` parameters to True while instantiating the class.

.. versionadded:: 1.1.1
Appelhoff, S., Sanderson, M., Brooks, T., Vliet, M., Quentin, R., Holdgraf, C., Chaumon, M., Mikulan, E., Tavabi, K., Hochenberger, R., Welke, D., Brunner, C., Rockhill, A., Larson, E., Gramfort, A. and Jas, M. (2019). MNE-BIDS: Organizing electrophysiological data into the BIDS format and facilitating their analysis. Journal of Open Source Software 4: (1896). https://doi.org/10.21105/joss.01896

Pernet, C. R., Appelhoff, S., Gorgolewski, K. J., Flandin, G., Phillips, C., Delorme, A., Oostenveld, R. (2019). EEG-BIDS, an extension to the brain imaging data structure for electroencephalography. Scientific Data, 6, 103. https://doi.org/10.1038/s41597-019-0104-8

---
Generated by MOABB 1.5.0 (Mother of All BCI Benchmarks)
https://github.com/NeuroTechX/moabb
