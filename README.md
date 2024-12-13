# StabilityFusion

StabilityFusion is a software designed to process, analyze, and visualize scientific and industrial data. This project integrates advanced computational techniques with a user-friendly interface, making it an invaluable tool for researchers and engineers working with stability data.

## Features

### 1. Comprehensive Data Processing
StabilityFusion offers a variety of data processing tools to ensure accurate and meaningful analysis:
- **Allan Deviation Analysis**: Compute stability of time-domain data using the Allan variance method. Error bar calculation is included to visualize uncertainty.
  *(TODO: Insert image here)*
- **Moving Average Calculation**: Smooth out short-term fluctuations in datasets to better visualize patterns that may reveal correlation between measurements.
  *(TODO: Insert image here)*

### 2. InfluxDB Integration
StabilityFusion seamlessly integrates with **InfluxDB**, a time-series database, to:
- Retrieve data directly from configured buckets.
- Simplify data acquisition and storage.
- Enable real-time analysis of incoming data streams.

### 3. Interactive User Interface
StabilityFusion includes an intuitive and interactive interface built using PyQt and PyQtGraph:
- **Parameter Tree**: Organize and configure data acquisition and processing settings in a hierarchical structure.
  *(TODO: Insert image here)*
- **Temporal Plotting Window**: Visualize the  time-domain data streams being analyzed, and interactively select a region of interest.
  *(TODO: Insert image here)*
- **Allan Deviation Plotting Window**: Analyze the stability of each measurement within the region of interest using Allan deviation plots.
  *(TODO: Insert image here)*
- **Dynamic Plot Management**: Easily show or hide individual plots for a clutter-free view.
  *(TODO: Insert image here)*
- **Bottom Table for Parameter Management**: Adjust sensitivity coefficients and fractional denominators for parameters:
  - Auto-calculate denominators based on the mean of data, to obtain the fractional stability.
  - Auto-calculate the sensitivity coefficients of measurements with respect to a main parameters (typically the local oscillator) to observe the stability contribution.
  - Manually input values for custom analysis.
  *(TODO: Insert image here)*
- **Preset Save and Load**: Effortlessly save and restore workspaces, including the parameter tree and parameter management table configurations. *(TODO: Insert image here)*
### 4. Configurable
- Flexible settings in `config/settings.json` to adapt to many projects.

### 5. Scalable Design
StabilityFusion is built to handle large datasets efficiently, ensuring smooth operation even with extensive time-series data.

<!-- ### 6. Uncertainty Analysis
The Allan deviation module includes uncertainty analysis:
- Calculate error bars for uncertainty representation.
- Flexible tau selection (decade, octave or all). -->

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/username/StabilityFusion.git
   ```
2. Navigate to the project directory:
   ```bash
   cd StabilityFusion
   ```
3. Install dependencies using your package manager (e.g., Pixi):
   ```bash
   pixi install
   ```

## Configuration

Create a configuration file (with the structure of `config/settings_example.json`) to configure database settings:
```json
{
    "influxdb": {
        "url": "http://localhost:8086",
        "token": "your_token",
        "org": "your_org",
        "bucket": "your_bucket"
    }
}
```

## Usage

1. Launch the application:
   ```bash
   python main.py
   ```
2. Use the interface to:
   - Retrieve data from InfluxDB.
   - Analyze data using Allan deviation and moving averages.
   - Customize plot settings and parameter adjustments.

## Example Workflow

1. **Connect to InfluxDB**: Retrieve data from a configured database bucket. *(TODO: Insert image here)*
2. **Visualize Time-Series Data**: Plot real-time data in the temporal plotting window. *(TODO: Insert image here)*
3. **Perform Stability Analysis**: Compute Allan deviation with error bars. *(TODO: Insert image here)*
4. **Fine-Tune Parameters**: Use the bottom table to adjust coefficients and toggle plot visibility. *(TODO: Insert image here)*
5. **Save Results**: Export analyzed data and visualizations for further reporting.

## Contributing

I welcome contributions to enhance StabilityFusion! To contribute:
1. Fork the repository.
2. Create a new branch for your feature or bug fix.
3. Submit a pull request for review.

## License

StabilityFusion is distributed under the GNU General Public License version 2 (GPLv2). For more details, please refer to the [LICENSE](LICENSE) file.

<!-- ## Acknowledgments

We thank all contributors and the open-source community for their support in developing this project. -->

