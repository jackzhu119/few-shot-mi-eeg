# A Multimodal NIRS-EEG Dataset for Unilateral Limb Motor Imagery

**MIND: Motor Imagery NIRS-EEG Dataset**

## Authors

Lufeng Feng[^1], Baomin Xu[^1], Haoran Zhang[^1], Bihai Lin[^1], Zuxuan Deng[^1], Sidi Tao[^1], Ziyu Jia[^2,*], Li Duan[^3,*]

[^1]: School of Computer Science and Technology, Beijing Jiaotong University, Beijing 100044, China  
[^2]: Institute of Automation, Chinese Academy of Sciences, Beijing 100044, China  
[^3]: School of Cyberspace Science and Technology, Beijing Jiaotong University, Beijing 100044, China  

*Corresponding authors:* Ziyu Jia (jia.ziyu@outlook.com); Li Duan (duanli@bjtu.edu.cn)

---

## Abstract

Motor imagery brain-computer interfaces (MI-BCIs) are promising for upper-limb rehabilitation and assistive control. However, most publicly available datasets are based on bilateral two-class or four-class paradigms and mainly rely on single-modal EEG, which limits their usefulness for fine-grained control of unilateral upper-limb movements. Distinguishing multiple directions or joint intentions within the same limb requires spatial information beyond what scalp EEG alone can provide. To address this gap, we present **MIND (Motor Imagery NIRS-EEG Dataset)**, a multimodal dataset that synchronously records electroencephalography (EEG) and functional near-infrared spectroscopy (fNIRS) during a four-direction unilateral upper-limb motor imagery task.

Thirty healthy right-handed college students aged 19 to 25 years were recruited, including 18 males and 12 females. Simultaneous 64-channel EEG based on the international 10–20 system and 51-channel fNIRS covering the sensorimotor and parietal cortices were recorded. Participants imagined moving the same upper limb in four planar directions: horizontal left-to-right, vertical top-to-bottom, diagonal upper-left to lower-right, and diagonal upper-right to lower-left. Each participant completed three blocks, corresponding to six sessions in total, including eyes-open rest, eyes-closed rest, and 120 MI trials with 30 trials per direction. The dataset provides raw recordings, event annotations, optical probe layout information, and standard preprocessed EEG in `.mat` format and fNIRS HbO and HbR data in `.csv` format, together with example scripts for data loading and preprocessing.

Baseline analyses of temporal-spectral features and conventional machine-learning and deep-learning classifiers show that multimodal EEG-fNIRS fusion improves four-class decoding performance relative to single-modal models. The MIND dataset provides a benchmark resource for developing and evaluating decoding algorithms, multimodal fusion methods, and rehabilitation-oriented unilateral MI-BCI systems.

### Keywords

- EEG, fNIRS, multimodal, motor imagery, unilateral upper limb, brain-computer interface

## Dataset Overview

- **Dataset title:** A Multimodal NIRS-EEG Dataset for Unilateral Limb Motor Imagery
- **Short name:** MIND: Motor Imagery NIRS-EEG Dataset
- **Modalities:** Electroencephalography (EEG), functional near-infrared spectroscopy (fNIRS)
- **Task type:** Unilateral upper-limb motor imagery with four directional commands
- **Data format:** BIDS-organized dataset. Standardized EEG is provided in BrainVision format (`.vhdr`, `.vmrk`, `.eeg`); standardized fNIRS is provided in `.snirf` format; raw recordings are stored in `sourcedata/`; preprocessed derivatives are stored in `derivatives/preproc-v1/`
- **Version:** `[v1.0 / 12-2025]`
- **Maintainer:** Lufeng Feng, Beijing Jiaotong University, lufeng.feng@bjtu.edu.cn

## Data Acquisition and Experimental Design

### Participants

- **Number of participants:** `[30]`
- **Sex:** `[18 males / 12 females]`
- **Age:** `[mean ± standard deviation, e.g., 21.4 ± 1.8 years]`
- **Handedness:** `[28 right-handed, 2 with no clear hand preference]`
- **Inclusion and exclusion criteria:**  
  `[Brief description, e.g., no neurological disorders, no history of psychiatric illness, normal vision and hearing, etc.]`

All participants provided written informed consent in accordance with the institutional ethics approval by the ethical committee of the Institute of Automation, Chinese Academy of Sciences (IA21-2504-020201).

- **Participant distribution:**

| Labeling type | Public participant IDs | #Subjects | Note |
| --- | --- | ---: | --- |
| Automatic event markers | sub-01 to sub-03, sub-10 to sub-12, sub-16 to sub-18, sub-19 to sub-20, sub-21 to sub-23, sub-24 to sub-25, sub-26 to sub-28 | 19 | Default device-based event markers |
| Manually labeled fNIRS events | sub-04 to sub-06, sub-07 to sub-09, sub-13 to sub-15, sub-29 to sub-30 | 11 | For sub-13, the first participant had missing fNIRS data |

### Task Paradigm and Session Structure

#### MI directions

Four two-dimensional unilateral upper-limb motor imagery directions were used, for example for the right arm:

1. Horizontal: left to right (`L2R`)
2. Vertical: top to bottom (`T2B`)
3. Diagonal: upper-left to lower-right (`LT2RB`)
4. Diagonal: upper-right to lower-left (`RT2LB`)

Participants were instructed to repeatedly imagine continuous movement of the same upper limb along the cued direction during the MI period in order to strengthen somatosensory and kinesthetic imagery.

#### Session structure

Each participant completed 6 sessions, organized into 3 session groups with 2 sessions per group.

Each session group included:

- 60 s eyes-open rest (`REST_EO`)
- 20 MI trials for horizontal and vertical directions (`L2R`, `T2B`)
- 60 s eyes-closed rest (`REST_EC`)
- 20 MI trials for the two diagonal directions (`LT2RB`, `RT2LB`)

This design helps improve the stability and repeatability of MI patterns across session groups.

#### Number of trials

- 20 MI trials per session, resulting in 6 × 20 = 120 MI trials per participant
- 30 trials per direction, resulting in 4 × 30 = 120 trials in total

#### Single-trial structure

- Total duration: 27 s
  - 0–2 s: visual cue with directional arrow
  - 2–12 s: sustained motor imagery; participants were instructed to imagine the movement 2 to 4 times within the 10 s interval
  - 12–27 s: rest with a white fixation cross on a black background to minimize eye movement and body motion

---

## Data Acquisition

### EEG Acquisition

- **Device:** Neuroscan synAmps2 wireless amplifier
- **Cap:** 64-channel solid-cap with Ag/AgCl electrodes based on the international 10–20 system
- **Reference and ground:**
  - Reference REF: parietal region
  - Ground GND: forehead
- **Sampling rate:** 1000 Hz
- **Impedance:** All electrode impedances were maintained below 10 kΩ during recording.
- **Notes:** The solid-cap configuration provides high current density, strong anti-interference capability, and low contact impedance.

- **Channel composition:**
  - EEG channels (64): `FP1`, `FPZ`, `FP2`, `AF3`, `AF4`, `F7`, `F5`, `F3`, `F1`, `FZ`, `F2`, `F4`, `F6`, `F8`, `FT7`, `FC5`, `FC3`, `FC1`, `FCZ`, `FC2`, `FC4`, `FC6`, `FT8`, `T7`, `C5`, `C3`, `C1`, `CZ`, `C2`, `C4`, `C6`, `T8`, `M1`, `TP7`, `CP5`, `CP3`, `CP1`, `CPZ`, `CP2`, `CP4`, `CP6`, `TP8`, `M2`, `P7`, `P5`, `P3`, `P1`, `PZ`, `P2`, `P4`, `P6`, `P8`, `PO7`, `PO5`, `PO3`, `POZ`, `PO4`, `PO6`, `PO8`, `CB1`, `O1`, `OZ`, `O2`, `CB2`
  - Auxiliary channels not used in analysis: `HEO`, `VEO`, `EKG`, `EMG`, `Trigger`

- **Original hardware filter settings:**
  - High-pass: 0.0 Hz
  - Low-pass: 500.0 Hz

### fNIRS Acquisition

- **Device:** LAB-NIRS continuous-wave fNIRS system (Shimadzu Corp., Kyoto, Japan)
- **Optodes:** 18 sources and 18 detectors forming 51 channels
- **Wavelengths:** `[e.g., 780 nm, 805 nm, 830 nm]`
- **Sampling rate:** 47.62 Hz
- **Measured signals:**
  - Oxygenated hemoglobin (HbO), deoxygenated hemoglobin (HbR), total hemoglobin (HbT)
  - Multi-wavelength absorbance signals (Abs780nm, Abs805nm, Abs830nm)
- **Optode layout:** Optodes were arranged according to the 10–20 system, and source-detector pairs mainly covered prefrontal, parietal, temporal, and sensorimotor regions.
- **Source-detector distance:** 30 mm to ensure appropriate cortical penetration depth. The source-detector pairing order is recorded in line 33 of the raw `.TXT` files, for example `(1,1)(2,1)(1,2)(3,1)...(18,18)`.
- **Fixation:** The optodes were fixed using an elastic cap to maintain stable contact throughout the experiment.

### Synchronization and Experimental Control

- **Software:** E-Prime 3.0 (E-Studio)
- **Triggers:**
  - E-Prime sent digital trigger signals simultaneously to the EEG and fNIRS acquisition systems to ensure precise temporal alignment between task events and physiological signals.
- **Environment:**
  - The experiment was conducted in a controlled environment to minimize ambient light interference and motion artifacts.
  - Participants were instructed to remain as still as possible.

---

## Data Records and Directory Structure

The current public release adopts a BIDS-organized structure and uses anonymized public participant IDs (`sub-01` to `sub-30`). The dataset root contains dataset-level description files, participant metadata files, a public subject ID policy file, the raw-recording directory `sourcedata/`, standardized participant directories `sub-*`, the derivatives directory `derivatives/`, and `.bidsignore` for excluding auxiliary files during validation. According to the released BIDS tree, raw vendor-format recordings are preserved in `sourcedata/`, standardized EEG and fNIRS data are stored in `sub-*`, and participant-level preprocessed derivatives are released in `derivatives/preproc-v1/`. In addition, the public release includes `README.md` at the dataset root and `subject_id_policy.json` documenting the anonymized subject-ID convention. 

```text
MIND_BIDS_PUBLIC/
├── README.md                         # Dataset-level documentation
├── .bidsignore                      # Ignore auxiliary non-BIDS files during validation
├── dataset_description.json         # Dataset-level metadata
├── participants.json                # Field descriptions for participants.tsv
├── participants.tsv                 # Participant-level metadata
├── derivatives/
│   └── preproc-v1/                  # Participant-level preprocessed derivatives
│       ├── dataset_description.json
│       ├── import_preproc_mapping.tsv
│       ├── import_preproc_summary.json
│       ├── README
│       ├── sub-01/
│       │   ├── eeg/
│       │   │   ├── sub-01_task-mi2d_desc-motorimagery_eeg.mat
│       │   │   ├── sub-01_task-mi2d_desc-motorimagery_eeg.json
│       │   │   ├── sub-01_task-mi2d_desc-rest_eeg.mat
│       │   │   └── sub-01_task-mi2d_desc-rest_eeg.json
│       │   └── nirs/
│       │       ├── sub-01_task-mi2d_desc-hbo_timeseries.csv
│       │       ├── sub-01_task-mi2d_desc-hbo_timeseries.json
│       │       ├── sub-01_task-mi2d_desc-hbr_timeseries.csv
│       │       └── sub-01_task-mi2d_desc-hbr_timeseries.json
│       ├── sub-13/
│       │   └── nirs/
│       │       └── sub-13_task-mi2d_notes.txt   # Special note for damaged fNIRS run
│       ├── ...
│       └── sub-30/
├── sourcedata/                      # Raw vendor-format recordings and manual event sources
│   ├── sub-01/
│   │   ├── eeg/
│   │   │   ├── sub-01_task-mi2d_run-01.dat
│   │   │   ├── sub-01_task-mi2d_run-01.ceo
│   │   │   ├── sub-01_task-mi2d_run-01.dap
│   │   │   ├── sub-01_task-mi2d_run-01.rs3
│   │   │   ├── ...
│   │   └── nirs/
│   │       ├── sub-01_task-mi2d_run-01.TXT
│   │       ├── sub-01_task-mi2d_run-01.csv
│   │       ├── ...
│   ├── sub-04/
│   │   └── nirs/
│   │       ├── sub-04_task-mi2d_desc-manualevents_events.csv
│   │       └── sub-04_task-mi2d_desc-manualevents_events.json
│   ├── sub-07/
│   │   └── nirs/
│   │       ├── sub-07_task-mi2d_run-01.TXT
│   │       ├── sub-07_task-mi2d_acq-a_run-02.TXT
│   │       ├── sub-07_task-mi2d_acq-b_run-02.TXT
│   │       ├── sub-07_task-mi2d_run-03.TXT
│   │       ├── sub-07_task-mi2d_desc-manualevents_events.csv
│   │       ├── sub-07_task-mi2d_run-02_1_manualevents_events.csv
│   │       └── sub-07_task-mi2d_run-02_2_manualevents_events.csv
│   ├── sub-13/
│   │   └── nirs/
│   │       ├── sub-13_task-mi2d_run-01.TXT
│   │       ├── sub-13_task-mi2d_run-03.TXT
│   │       └── sub-13_task-mi2d_desc-manualevents_events.csv
│   ├── ...
│   └── sub-30/
├── sub-01/                          # Standardized BIDS participant directory
│   ├── eeg/
│   │   ├── sub-01_coordsystem.json
│   │   ├── sub-01_electrodes.tsv
│   │   ├── sub-01_task-mi2d_run-01_eeg.vhdr
│   │   ├── sub-01_task-mi2d_run-01_eeg.vmrk
│   │   ├── sub-01_task-mi2d_run-01_eeg.eeg
│   │   ├── sub-01_task-mi2d_run-01_events.tsv
│   │   ├── sub-01_task-mi2d_run-01_events.json
│   │   ├── sub-01_task-mi2d_run-01_channels.tsv
│   │   ├── sub-01_task-mi2d_run-01_eeg.json
│   │   ├── ...
│   └── nirs/
│       ├── sub-01_coordsystem.json
│       ├── sub-01_optodes.tsv
│       ├── sub-01_task-mi2d_run-01_nirs.snirf
│       ├── sub-01_task-mi2d_run-01_events.tsv
│       ├── sub-01_task-mi2d_run-01_events.json
│       ├── sub-01_task-mi2d_run-01_channels.tsv
│       ├── sub-01_task-mi2d_run-01_nirs.json
│       ├── ...
├── sub-07/
│   └── nirs/
│       ├── sub-07_task-mi2d_acq-a_run-02_nirs.snirf
│       ├── sub-07_task-mi2d_acq-a_run-02_events.tsv
│       ├── sub-07_task-mi2d_acq-b_run-02_nirs.snirf
│       └── sub-07_task-mi2d_acq-b_run-02_events.tsv
├── sub-13/
│   └── nirs/
│       ├── sub-13_task-mi2d_run-01_nirs.snirf
│       └── sub-13_task-mi2d_run-03_nirs.snirf
├── ...
└── sub-30/
```

### Top-level files

- **`README.md`**: Dataset-level documentation for the public release.
- **`.bidsignore`**: Used to ignore auxiliary non-BIDS files during validation.
- **`dataset_description.json`**: Dataset name, version, authorship, release, and BIDS-version information.
- **`participants.tsv`**: Participant-level metadata table.
- **`participants.json`**: Semantic descriptions for all fields in `participants.tsv`.
- **`subject_id_policy.json`**: Description of the anonymized public participant-ID scheme.
- **`derivatives/`**: Derivatives directory. The current public release provides `preproc-v1`.
- **`sourcedata/`**: Raw vendor-format EEG and fNIRS recordings, together with preserved manual event-source files for manually labeled fNIRS participants.
- **`sub-*`**: Standardized BIDS participant directories.

### Raw recording directory: `sourcedata`

`sourcedata/` stores original vendor-format recordings organized by public BIDS participant ID. Each participant directory contains `eeg/` and `nirs/` subdirectories. EEG recordings are preserved in Curry raw format, while fNIRS recordings are preserved as vendor-exported `TXT` and `csv` files. For participants requiring manual fNIRS event labeling, `sourcedata/sub-*/nirs/` also includes `desc-manualevents_events.csv` and `desc-manualevents_events.json` files to preserve event provenance. For the interrupted second fNIRS acquisition of `sub-07`, two additional split label files, `run-02_1_manualevents_events.*` and `run-02_2_manualevents_events.*`, are provided to preserve alignment with the two physical sub-recordings. For `sub-13`, only `run-01` and `run-03` raw fNIRS files are preserved because the second acquisition was damaged. 

```text
sourcedata/
├── sub-01/
│   ├── eeg/
│   │   ├── sub-01_task-mi2d_run-01.dat
│   │   ├── sub-01_task-mi2d_run-01.ceo
│   │   ├── sub-01_task-mi2d_run-01.dap
│   │   ├── sub-01_task-mi2d_run-01.rs3
│   │   ├── sub-01_task-mi2d_run-02.dat
│   │   ├── sub-01_task-mi2d_run-03.dat
│   │   └── ...
│   └── nirs/
│       ├── sub-01_task-mi2d_run-01.TXT
│       ├── sub-01_task-mi2d_run-01.csv
│       ├── sub-01_task-mi2d_run-02.TXT
│       ├── sub-01_task-mi2d_run-02.csv
│       ├── sub-01_task-mi2d_run-03.TXT
│       └── ...
├── sub-04/
│   └── nirs/
│       ├── sub-04_task-mi2d_desc-manualevents_events.csv
│       └── sub-04_task-mi2d_desc-manualevents_events.json
├── sub-07/
│   └── nirs/
│       ├── sub-07_task-mi2d_run-01.TXT
│       ├── sub-07_task-mi2d_acq-a_run-02.TXT
│       ├── sub-07_task-mi2d_acq-b_run-02.TXT
│       ├── sub-07_task-mi2d_run-03.TXT
│       ├── sub-07_task-mi2d_desc-manualevents_events.csv
│       ├── sub-07_task-mi2d_run-02_1_manualevents_events.csv
│       └── sub-07_task-mi2d_run-02_2_manualevents_events.csv
├── sub-13/
│   └── nirs/
│       ├── sub-13_task-mi2d_desc-manualevents_events.csv
│       ├── sub-13_task-mi2d_run-01.TXT
│       └── sub-13_task-mi2d_run-03.TXT
├── ...
└── sub-30/
```

#### Raw EEG files in `sourcedata`

Each participant has three runs of Curry EEG files in `sourcedata/sub-*/eeg/`. Each run includes the following four file types:

- **`.dat`**: Main continuous raw EEG data file.
- **`.ceo`**: Project-level metadata and experiment-configuration file.
- **`.dap`**: Acquisition-parameter file, such as sampling rate, filter settings, and gain.
- **`.rs3`**: Spatial layout and device-configuration file.

#### Raw fNIRS files in `sourcedata`

Each participant has raw vendor-format fNIRS files in `sourcedata/sub-*/nirs/`:

- **`.TXT`**: Continuous time series and multichannel measurements, including oxyHb, deoxyHb, totalHb, and multi-wavelength absorbance signals.
- **`.csv`**: Original timing information and device-exported fields.
- **`desc-manualevents_events.csv` / `.json`**: Preserved manual event-source files for participants whose fNIRS event timing required manual curation.
- **`run-02_1_manualevents_events.*` and `run-02_2_manualevents_events.*`**: Segment-specific manual event-source files used only for the interrupted split fNIRS acquisition of `sub-07`.

Most participants retain three runs of paired `TXT` and `csv` files. There are two special cases:

- **The second fNIRS run for `sub-07`**: Due to equipment interruption during acquisition, the second recording is preserved in `sourcedata/sub-07/nirs/` as two physical segments, `acq-a_run-02` and `acq-b_run-02`. The corresponding segment-specific manual event-source files are also preserved.
- **The second fNIRS run for `sub-13`**: Due to corruption of the original recording, only the raw files for `run-01` and `run-03` are preserved in `sourcedata/sub-13/nirs/`.

### Standardized participant directories

Each `sub-*` directory corresponds to one participant and contains `eeg/` and `nirs/` subdirectories storing standardized EEG and fNIRS data, respectively.

#### EEG files in `sub-*/eeg`

EEG data are standardized into the BrainVision triplet and accompanied by event, channel, electrode, and coordinate-system information. Each participant has standardized files for `run-01`, `run-02`, and `run-03`. For example:

```text
sub-01/
└── eeg/
    ├── sub-01_coordsystem.json
    ├── sub-01_electrodes.tsv
    ├── sub-01_task-mi2d_run-01_channels.tsv
    ├── sub-01_task-mi2d_run-01_eeg.eeg
    ├── sub-01_task-mi2d_run-01_eeg.json
    ├── sub-01_task-mi2d_run-01_eeg.vhdr
    ├── sub-01_task-mi2d_run-01_eeg.vmrk
    ├── sub-01_task-mi2d_run-01_events.json
    ├── sub-01_task-mi2d_run-01_events.tsv
    ├── sub-01_task-mi2d_run-02_channels.tsv
    ├── sub-01_task-mi2d_run-02_eeg.eeg
    ├── ...
    └── sub-01_task-mi2d_run-03_events.tsv
```

File descriptions:

- **`.vhdr`, `.vmrk`, `.eeg`**: BrainVision triplet.
- **`*_events.tsv` and `*_events.json`**: Event timing, duration, labels, and descriptions.
- **`*_channels.tsv`**: EEG channel definitions.
- **`*_eeg.json`**: EEG modality-level metadata.
- **`*_electrodes.tsv`**: EEG electrode spatial coordinates.
- **`*_coordsystem.json`**: EEG coordinate-system description.

#### fNIRS files in `sub-*/nirs`

fNIRS data are standardized into SNIRF and accompanied by event, channel, optode, and coordinate-system information. Most participants have standardized files for `run-01`, `run-02`, and `run-03`. The interrupted second fNIRS acquisition of `sub-07` is represented as `acq-a_run-02` and `acq-b_run-02`, whereas `sub-13` contains only `run-01` and `run-03` because the second run was damaged. For example:

```text
sub-01/
└── nirs/
    ├── sub-01_coordsystem.json
    ├── sub-01_optodes.tsv
    ├── sub-01_task-mi2d_run-01_channels.tsv
    ├── sub-01_task-mi2d_run-01_events.json
    ├── sub-01_task-mi2d_run-01_events.tsv
    ├── sub-01_task-mi2d_run-01_nirs.json
    ├── sub-01_task-mi2d_run-01_nirs.snirf
    ├── sub-01_task-mi2d_run-02_channels.tsv
    ├── ...
    └── sub-01_task-mi2d_run-03_nirs.snirf
```

File descriptions:

- **`*.snirf`**: Standardized fNIRS data file. The current release stores processed HbO and HbR time series.
- **`*_events.tsv` and `*_events.json`**: Event timing, duration, labels, and descriptions.
- **`*_channels.tsv`**: fNIRS measurement-channel definitions.
- **`*_nirs.json`**: fNIRS modality-level metadata.
- **`*_optodes.tsv`**: Three-dimensional positions of sources and detectors.
- **`*_coordsystem.json`**: fNIRS coordinate-system description.

### Special cases

- **`sub-07`**
  - The second fNIRS acquisition was interrupted during recording.
  - In `sourcedata/sub-07/nirs/`, the raw recording is preserved as two physical segments, `acq-a_run-02` and `acq-b_run-02`, together with segment-specific manual event-source files for the `_1` and `_2` recordings.
  - In `sub-07/nirs/`, the standardized BIDS files are correspondingly preserved as two groups: `sub-07_task-mi2d_acq-a_run-02_*` and `sub-07_task-mi2d_acq-b_run-02_*`.

- **`sub-13`**
  - The second fNIRS run was corrupted.
  - In the current release, `sub-13/nirs/` includes standardized BIDS files only for `run-01` and `run-03`.
  - Correspondingly, `sourcedata/sub-13/nirs/` preserves only the raw files for `run-01` and `run-03`, together with the participant-level manual event-source file.


---

## Preprocessing and Quality Control

### Preprocessed data directory

Preprocessed results are currently released as BIDS derivatives in `derivatives/preproc-v1/` rather than in a separate top-level `Dataset Preprocessing/` directory parallel to the main dataset. The structure is illustrated below:

```text
MIND_BIDS/
└── derivatives/
    └── preproc-v1/
        ├── dataset_description.json
        ├── import_preproc_summary.json
        ├── README
        ├── sub-01/
        │   ├── eeg/
        │   │   ├── sub-01_task-mi2d_desc-motorimagery_eeg.mat
        │   │   ├── sub-01_task-mi2d_desc-motorimagery_eeg.json
        │   │   ├── sub-01_task-mi2d_desc-rest_eeg.mat
        │   │   └── sub-01_task-mi2d_desc-rest_eeg.json
        │   └── nirs/
        │       ├── sub-01_task-mi2d_desc-hbo_timeseries.csv
        │       ├── sub-01_task-mi2d_desc-hbo_timeseries.json
        │       ├── sub-01_task-mi2d_desc-hbr_timeseries.csv
        │       └── sub-01_task-mi2d_desc-hbr_timeseries.json
        ├── sub-02/
        ├── sub-03/
        ├── ...
        └── sub-30/
```

`derivatives/preproc-v1/` stores **participant-level** preprocessed results rather than run-level derivative files. EEG preprocessing outputs are saved as `.mat` files, while fNIRS preprocessing outputs are saved as `.csv` files for HbO and HbR, each accompanied by a `.json` sidecar description file.

- **Naming convention for preprocessed files**

  - **EEG**
    - `sub-XXXX/eeg/sub-XXXX_task-mi2d_desc-motorimagery_eeg.mat`  
      Stores participant-level preprocessed EEG data and event information for all MI tasks.
    - `sub-XXXX/eeg/sub-XXXX_task-mi2d_desc-rest_eeg.mat`  
      Stores participant-level preprocessed EEG data for resting-state segments, including both eyes-open and eyes-closed rest.

  - **fNIRS**
    - `sub-XXXX/nirs/sub-XXXX_task-mi2d_desc-hbo_timeseries.csv`: preprocessed HbO data for the participant
    - `sub-XXXX/nirs/sub-XXXX_task-mi2d_desc-hbr_timeseries.csv`: preprocessed HbR data for the participant

    **Data shape information:**
    - Data are stored in the form `[[n_epoch, n_channel*time_points], label]`
    - `time_points = [-5, 25] × sampling rate`
    - Sampling rate = 10 Hz

#### Structure of `motor_imagery_events.mat`

Each motor imagery data file contains the following variables:

| Variable name | Dimension | Description |
| --- | --- | --- |
| preprocessed_data | 64×6250×120 | Preprocessed EEG data, arranged as channels × time points × trials. There are 64 EEG channels. Each trial contains 25 s of data from −5 s to 20 s at 250 Hz. A total of 120 trials are included. |
| srate | scalar | Sampling rate, 250 Hz |
| label | 4×120 | One-hot encoded trial labels. The four rows correspond to the four MI tasks: left-to-right, top-to-bottom, upper-left to lower-right, and upper-right to lower-left. |
| ch_names | 1×64 | Names of the 64 EEG channels |
| bads | array | Names of bad channels, if present |
| bad_index | array | Indices of bad channels, for use in EEGLAB-based bad-channel handling |

#### Structure of `resting_state_events.mat`

Each resting-state data file contains the following variables:

| Variable name | Dimension | Description |
| --- | --- | --- |
| preprocessed_data | 64×15000×6 single | Preprocessed EEG data, arranged as channels × time points × trials. There are 64 EEG channels. Each event contains 60 s of data from 0 to 60 s at 250 Hz. A total of 6 trials are included. |
| srate | scalar | Sampling rate, 250 Hz |
| label | 2×6 | One-hot encoded labels for resting-state trials. The two rows correspond to eyes-open rest and eyes-closed rest. |
| ch_names | 1×64 | Names of the 64 EEG channels |
| bads | array | Names of bad channels, if present |
| bad_index | array | Indices of bad channels, for use in EEGLAB-based bad-channel handling |

Researchers can directly load `.mat` files in MATLAB using `load()`, or in Python using `scipy.io.loadmat()`. Preprocessed fNIRS files can be directly loaded using `pandas.read_csv()`.

### EEG preprocessing pipeline

MNE-Python was used for EEG preprocessing with the following steps:

1. **Band-pass filtering:** 0.5–50 Hz to remove low-frequency drift and high-frequency noise.
2. **Notch filtering:** 50 Hz to suppress power-line interference.
3. **Bad channel detection and interpolation:**
   - Bad channels were identified based on amplitude, variance, and visual inspection.
   - Spherical interpolation was used to reconstruct bad channels.
4. **Segmentation:**
   - MI segments: 25 s, including 5 s cue period, 10 s MI execution, and 10 s post-imagery rest
   - Resting segments: 60 s for eyes-open or eyes-closed rest
5. **Baseline correction:**
   - A −2 to 0 s window before each segment was used as the baseline.
6. **Down-sampling:**
   - Data were down-sampled from 1000 Hz to 250 Hz.
7. **Independent component analysis and artifact removal:**
   - ICA decomposition was performed, for example retaining 30 components.
   - ICLabel or manual inspection was used to remove components related to eye movement, muscle activity, ECG, and channel noise.
8. **Exported files:**
   - `subject_##_motor_imagery_events.mat`: MI trial data with shape trial × channel × time, together with labels
   - `subject_##_resting_state_events.mat`: resting-state data

### fNIRS preprocessing pipeline

1. **Raw data reading (`TXT` + `CSV`)**
   - `.TXT`: light intensity and metadata. Starting from line 35, the file contains time-point-level data. The string `0Z` was replaced by `00` before parsing.
   - `.csv`: contains experiment start time and several record entries.
   - `Pre.Rest / Task / Pos.Rest` fields in `.csv` were not directly used as event boundaries and were treated only as references.

2. **Time parsing and label extraction**

```python
def time_s(time_str):
    hours, minutes, seconds = time_str.split(':')
    if '.' in seconds:
        seconds, milliseconds = seconds.split('.')
    else:
        milliseconds = '0'
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds) + float(milliseconds) / 1000
```

- **Automatic labeling:** For most participants, task onset time and task type were read from line 9 onward in the `.csv` file.
- **Participants with manually labeled fNIRS data:** `sub-04` to `sub-06`, `sub-07` to `sub-09`, `sub-13` to `sub-15`, and `sub-29` to `sub-30`
  - Key time points were manually marked in the vendor software.
  - `Time(sec)` entries with `Mark == 1` were extracted from the `.TXT` file.
  - Event onset times were computed according to the experimental paradigm and written into the `mrk_time` field of the corresponding manual event source file.

3. **Band-pass filtering (0.02–0.2 Hz)**

A third-order Butterworth band-pass filter was used:

```python
def butter_bandpass(lowcut, highcut, fs, order=3):
    nyq = 0.5 * fs
    low = lowcut / nyq
    high = highcut / nyq
    b, a = butter(order, [low, high], btype='band')
    return b, a

def butter_bandpass_filter(data, lowcut, highcut, fs, order=3):
    b, a = butter_bandpass(lowcut, highcut, fs, order=order)
    return lfilter(b, a, data)
```

4. **Construction of MNE Raw objects and annotations**

- For each session, 51-channel HbO and HbR `mne.io.RawArray` objects were constructed.
- Event times were used to create `annotations.onset`.
- `annotations.duration` was assigned using `time_map = {'1': 60, '2': 60, '3': 30, '4': 10, '5': 10, '6': 10, '7': 10}`.
- `annotations.description` used `'1', '2', '4', '5', '6', '7'` as event labels.

```python
Indic = range(len(label_time_list[idx]))
oxy_raw.annotations.onset = np.array([label_time_list[idx][i] for i in Indic])

time_map = {'1': 60, '2': 60, '3': 30, '4': 10, '5': 10, '6': 10, '7': 10}
oxy_raw.annotations.duration = np.array([time_map[label_list[idx][i]] for i in Indic])
oxy_raw.annotations.description = np.array([label_list[idx][i] for i in Indic])
```

5. **Down-sampling and epoching**

- Sampling rate was down-sampled to 10 Hz.
- HbO and HbR epochs were constructed using `tmin = -5 s` and `tmax = 25 s`.
- Baseline correction used the interval −5 to 0 s.

```python
events, event_dict = mne.events_from_annotations(oxy_raw)
oxy_raw.resample(new_sfreq)
deoxy_raw.resample(new_sfreq)

oxy_epochs = mne.Epochs(
    oxy_raw, events, event_id=event_dict,
    tmin=tmin, tmax=tmax,
    reject_by_annotation=True,
    proj=True,
    baseline=(None, 0),
    preload=True,
)
oxy_epochs.apply_baseline((-5, 0))
```

- The same processing was applied to HbR to generate `deoxy_epochs`.

6. **Flattening into trial × feature tables and export**

- For each participant and for HbO and HbR separately:
  - Epochs for each event type were extracted with shape `[n_epochs, n_channels, n_times]`
  - Data were reshaped into `[n_epochs, n_channels * n_times]`
  - A `label` column was appended
- All sessions were concatenated and saved as `hbo.csv` and `hbr.csv`.

For example, for event labels `['1', '2', '4', '5', '6', '7']`:

```python
for event_name in name_list_1:
    e = oxy_epochs[event_name]
    data = e.get_data()        # (n_epochs, n_channels, n_times)
    data_flat = data.reshape(n_epochs, -1)
    df = pd.DataFrame(data_flat)
    df['label'] = event_name
    oxy_df_all = pd.concat([oxy_df_all, df], ignore_index=True)
```

The same procedure was applied to HbR to obtain `deoxy_df_all`.

Finally:

```python
oxy_df_all.to_csv(".../sub_XX/hbo.csv", index=False)
deoxy_df_all.to_csv(".../sub_XX/hbr.csv", index=False)
```

For participants with manual event labeling, the only difference is that `label_time_list` was taken from the `mrk_time` field of the corresponding manual event source file. The remaining preprocessing steps were identical.

### Quality control

- **EEG**
  - All electrode impedances were checked to remain below 10 kΩ.
  - Bad channels were interpolated when necessary.
  - Raw waveforms and power spectra were inspected to identify eye, muscle, and motion artifacts.
  - ICA was used to remove major physiological artifacts.

- **fNIRS**
  - Raw light intensity signals were inspected for saturation, overly high values, or overly low values, and abnormal channels were flagged.
  - Participants with manual event labeling used an independent event-marking procedure to ensure consistent event timing.
  - After preprocessing, the number of trials for each event type was checked against the experimental design, allowing for exceptions caused by equipment failure.

---

## Usage Notes

### Example for reading raw EEG data in Python with MNE

```python
import mne

file_path = "Dataset raw/xxx/EEG/Acquisition 05.dat"
raw = mne.io.read_raw_curry(file_path, preload=True)

print(raw.info)
print(raw.ch_names)
print(raw.annotations)

events, event_dict = mne.events_from_annotations(raw)
print(events[:5], event_dict)
```

### Example for reading preprocessed EEG `.mat` files in Python

```python
from scipy.io import loadmat

mat = loadmat("Dataset Preprocessing/EEG/xxx/EEG/subject_01_motor_imagery_events.mat")
data = mat['data']
labels = mat['labels']
```

### Example for reading raw fNIRS data (`TXT` + `CSV`)

```python
import pandas as pd
import numpy as np

def read_txt(file_path):
    lines = []
    with open(file_path, 'r') as f:
        for line in f:
            lines.append(line)
    return lines

txt_path = "Dataset raw/xxx/fNIRS/xxx-001.TXT"
csv_path = "Dataset raw/xxx/fNIRS/xxx-001.csv"

lines = read_txt(txt_path)
lines[35] = lines[35].replace('0Z', '00')
datas = [list(map(float, l[:-1].split('\t'))) for l in lines[35:]]

index = [lines[33][:-1].split('\t    ')[i] + lines[34][:-1].split('\t')[i]
         for i in range(len(lines[33].split('\t')))]

data_pd = pd.DataFrame(np.array(datas), columns=index)
label_csv = pd.read_csv(csv_path, header=None, names=range(5))
```

### Example for reading preprocessed fNIRS HbO and HbR files in Python

```python
import pandas as pd

hbo = pd.read_csv("Dataset Preprocessing/NIRS/sub_*/hbo.csv")
hbr = pd.read_csv("Dataset Preprocessing/NIRS/sub_*/hbr.csv")

X_hbo = hbo.drop(columns=['label']).values
y = hbo['label'].values
```

More complete preprocessing and analysis examples are provided in the `code/` directory.

---

## Code Availability

- The `code/` directory provides:
  - Scripts for reading and preprocessing raw EEG data with MNE-Python
  - Scripts for parsing raw fNIRS `.TXT` and `.csv` files, reading manually labeled event times, band-pass filtering, and epoch construction
  - Example EEG and fNIRS visualization scripts

A Python 3.10 or later environment with `mne`, `numpy`, `scipy`, `pandas`, and `matplotlib` is recommended.
