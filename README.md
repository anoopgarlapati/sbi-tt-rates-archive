# SBI TT Rates Archive

This repository serves as an archive containing historical SBI TT rates since 02 July 2020. These rates are one of the important rates required for ITR (Income Tax Return) purposes and are unfortunately not made readily available by RBI (Reserve Bank of India) or SBI (State Bank of India).

This repository is forked from [skbly7/sbi-tt-rates-historical](https://github.com/skbly7/sbi-tt-rates-historical)

> [!NOTE]
> This repository is maintained to provide historical data on SBI TT rates. The rates are collected and stored automatically, and while efforts are made to ensure accuracy, no guarantees can be made regarding the completeness or correctness of the data.

## Overview

The repository is structured to maintain the SBI TT rates in a directory format based on the year and month of the rate data. Each rate file is saved with a timestamp to indicate the exact date and time it was retrieved.

## Directory Structure

The files are organized in the following directory structure:
```
├── 2020
│ ├── 07
│ │ ├── 2020-07-02-00:00.pdf
│ │ ├── ...
│ ├── ...
├── 2021
│ ├── 01
│ │ ├── 2021-01-01-00:00.pdf
│ │ ├── ...
│ ├── ...
├── ...
```

Each file is named in the format `YYYY-MM-DD-HH:MM.pdf`, where `YYYY` is the year, `MM` is the month, `DD` is the day, and `HH:MM` is the hour and minute when the SBI TT Rates file was retrieved.

## Usage

You can browse the directories to find the historical SBI TT rates for specific dates. The rates are saved as PDF files and can be viewed using any standard PDF viewer.

## Automation

This repository is automatically updated twice daily using a GitHub Action. The action downloads the latest SBI TT rates and commits the updates to the repository. This ensures that the repository stays up-to-date with the latest available rates.

## Contributions
Contributions are welcome!  
If you have any improvements or suggestions, feel free to open an issue or submit a pull request.

