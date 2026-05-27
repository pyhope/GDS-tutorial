"""Plot GDS proximity-summary outputs.

Author:
	Haiyang Luo; Akash Gupta

Overview:
	This script plots ``sum_proximity_*.txt`` files produced by the GDS
	similarity workflow. It reads the species list and ``nw`` value from the
	commented file header, assigns the corresponding phase-count columns, plots
	Phase A, Phase B, and Interface counts for each species, and reserves the
	final row for ``lw`` and ``chi``. It also calculates simple plateau statistics
	from the final fraction of frames and writes them to a text file.

Sample commands:
	python scripts/plot_similarity.py runs/mass_only/nw2/sum_proximity_0_1.txt

	cd runs/mass_only/nw2
	python ../../scripts/plot_similarity.py

	python scripts/plot_similarity.py \
		runs/mass_only/nw2/sum_proximity_0_1.txt \
		--plateau-fraction 0.2 \
		--output elemental_evolution_with_plateau_stats.pdf \
		--stats-output plateau_stats.txt
"""

import argparse
import math
from pathlib import Path
from typing import Sequence

import matplotlib.pyplot as plt
import pandas as pd


def parse_arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
	"""Parse command-line arguments.

	Args:
		argv: Optional command-line argument vector. If None, argparse reads
			from sys.argv.

	Returns:
		Parsed command-line arguments.
	"""
	parser = argparse.ArgumentParser(
		description="Plot GDS sum_proximity output with species inferred from the id header."
	)
	parser.add_argument(
		"file",
		nargs="?",
		help="Input sum_proximity file. Default: first sum_proximity_*.txt in the current directory.",
	)
	parser.add_argument(
		"--plateau-fraction",
		type=float,
		default=0.2,
		help="Fraction of final frames used for plateau statistics. Default: 0.2",
	)
	parser.add_argument(
		"--output",
		default="elemental_evolution_with_plateau_stats.pdf",
		help="Output figure path. Default: elemental_evolution_with_plateau_stats.pdf",
	)
	parser.add_argument(
		"--stats-output",
		default="plateau_stats.txt",
		help="Output plateau statistics path. Default: plateau_stats.txt",
	)
	return parser.parse_args(argv)


def resolve_input_path(file_argument: str | None) -> Path:
	"""Resolve the input summary path.

	Args:
		file_argument: Optional input file from the command line.

	Returns:
		Input path to read.

	Raises:
		FileNotFoundError: If no explicit file is provided and no matching
			``sum_proximity_*.txt`` file exists in the current directory.
	"""
	if file_argument:
		return Path(file_argument)

	matching_files = sorted(Path.cwd().glob("sum_proximity_*.txt"))
	if not matching_files:
		raise FileNotFoundError(
			"No input file was provided and no sum_proximity_*.txt file was found "
			f"in {Path.cwd()}."
		)
	return matching_files[0]


def read_species_from_id_header(input_path: Path) -> list[str]:
	"""Read species labels from the commented ``id`` header line.

	Args:
		input_path: Path to a GDS ``sum_proximity`` text file.

	Returns:
		Species labels between ``id`` and the trailing ``lw chi`` columns.

	Raises:
		ValueError: If the expected ``id`` header line is missing or malformed.
	"""
	with input_path.open() as file_object:
		for line in file_object:
			stripped_line = line.strip()
			if not stripped_line.startswith("#"):
				continue
			header_tokens = stripped_line.lstrip("#").split()
			if header_tokens and header_tokens[0] == "id":
				if len(header_tokens) < 4 or header_tokens[-2:] != ["lw", "chi"]:
					raise ValueError(
						f"Malformed id header in {input_path}: expected trailing 'lw chi'."
					)
				return header_tokens[1:-2]
	raise ValueError(f"Could not find a commented 'id ... lw chi' header in {input_path}.")


def read_nw_from_header(input_path: Path) -> str:
	"""Read the interface-width multiplier from the commented ``nw`` header line.

	Args:
		input_path: Path to a GDS ``sum_proximity`` text file.

	Returns:
		The parsed ``nw`` value, or ``unknown`` if the header is absent.
	"""
	with input_path.open() as file_object:
		for line in file_object:
			header_tokens = line.strip().lstrip("#").split()
			if len(header_tokens) >= 3 and header_tokens[0] == "nw" and header_tokens[1] == "=":
				return header_tokens[2]
	return "unknown"


def build_column_names(species: Sequence[str]) -> list[str]:
	"""Build dataframe column names for a GDS proximity summary.

	Args:
		species: Species labels read from the header.

	Returns:
		Column names for index, three phase counts per species, lw, and chi.
	"""
	column_names = ["index"]
	for element in species:
		column_names.extend(
			[
				f"{element}_solid",
				f"{element}_liquid",
				f"{element}_interface",
			]
		)
	column_names.extend(["lw", "chi"])
	return column_names


def read_summary(input_path: Path, species: Sequence[str]) -> pd.DataFrame:
	"""Read a GDS proximity summary into a dataframe.

	Args:
		input_path: Path to the input summary file.
		species: Species labels that define the expected columns.

	Returns:
		Dataframe with explicit column names.

	Raises:
		ValueError: If the data column count does not match the header.
	"""
	dataframe = pd.read_csv(input_path, comment="#", sep=r"\s+", header=None)
	column_names = build_column_names(species)
	if dataframe.shape[1] != len(column_names):
		raise ValueError(
			f"{input_path} has {dataframe.shape[1]} data columns, but the id header implies "
			f"{len(column_names)} columns."
		)
	dataframe.columns = column_names
	return dataframe


def get_species_totals(dataframe: pd.DataFrame, species: Sequence[str]) -> dict[str, int]:
	"""Calculate total atom count per species from the first data row.

	Args:
		dataframe: Summary dataframe.
		species: Species labels to summarize.

	Returns:
		Mapping from species label to total atom count.
	"""
	totals: dict[str, int] = {}
	first_row = dataframe.iloc[0]
	for element in species:
		total = (
			first_row[f"{element}_solid"]
			+ first_row[f"{element}_liquid"]
			+ first_row[f"{element}_interface"]
		)
		totals[element] = int(round(total))
	return totals


def get_plateau_indices(dataframe: pd.DataFrame, plateau_fraction: float) -> pd.Index:
	"""Select final-row indices used for plateau statistics.

	Args:
		dataframe: Summary dataframe.
		plateau_fraction: Fraction of final rows to include.

	Returns:
		Index labels for the selected plateau rows.

	Raises:
		ValueError: If ``plateau_fraction`` is outside ``(0, 1]``.
	"""
	if plateau_fraction <= 0 or plateau_fraction > 1:
		raise ValueError("--plateau-fraction must be greater than 0 and at most 1.")
	num_plateau_rows = max(1, int(len(dataframe) * plateau_fraction))
	return dataframe.index[-num_plateau_rows:]


def plot_series_with_plateau(
	axis: plt.Axes,
	x_values: pd.Series,
	y_values: pd.Series,
	plateau_indices: pd.Index,
	label: str,
	color: str,
	value_format: str,
) -> tuple[float, float]:
	"""Plot a time series with plateau mean and standard-deviation shading.

	Args:
		axis: Matplotlib axis to draw on.
		x_values: Frame/index values.
		y_values: Data series to plot.
		plateau_indices: Row indices used for plateau statistics.
		label: Legend label.
		color: Matplotlib color.
		value_format: Format string for mean/std annotations.

	Returns:
		Mean and standard deviation over the selected plateau region.
	"""
	plateau_values = y_values.iloc[plateau_indices]
	mean = plateau_values.mean()
	standard_deviation = plateau_values.std()

	axis.plot(x_values, y_values, label=label, linestyle="-", color=color)
	axis.axhline(mean, linestyle="--", color=color, alpha=0.7)
	axis.fill_between(x_values, mean - standard_deviation, mean + standard_deviation, color=color, alpha=0.2)
	axis.annotate(
		f"{mean:{value_format}}+/-{standard_deviation:{value_format}}",
		xy=(x_values.iloc[-1], mean + standard_deviation + 0.02 * (axis.get_ylim()[1] - axis.get_ylim()[0])),
		xytext=(-50, 0),
		textcoords="offset points",
		color=color,
		fontsize=8,
		ha="right",
		va="bottom",
		arrowprops={"arrowstyle": "-", "color": color, "lw": 0.5},
	)
	return mean, standard_deviation


def plot_summary(
	dataframe: pd.DataFrame,
	species: Sequence[str],
	plateau_indices: pd.Index,
	output_path: Path,
	input_path: Path,
	nw_value: str,
) -> None:
	"""Plot species counts plus ``lw`` and ``chi`` in the final row.

	Args:
		dataframe: Summary dataframe.
		species: Species labels to plot.
		plateau_indices: Row indices used for plateau statistics.
		output_path: Figure output path.
		input_path: Input summary file path.
		nw_value: Interface-width multiplier read from the file header.
	"""
	num_species_rows = math.ceil(len(species) / 2)
	num_rows = num_species_rows + 1
	figure, axes = plt.subplots(num_rows, 2, figsize=(12, 3 * num_rows))
	axes = axes.flatten()

	species_totals = get_species_totals(dataframe=dataframe, species=species)
	species_title = ", ".join(f"{species_totals[element]} {element}" for element in species)
	figure.suptitle(
		f"Species: [{species_title}]\n"
		f"nw = {nw_value}; file = {input_path.name}",
		y=0.985,
	)

	phases = ["solid", "liquid", "interface"]
	phase_labels = {"solid": "Phase A", "liquid": "Phase B", "interface": "Interface"}
	colors = {"solid": "tab:blue", "liquid": "tab:orange", "interface": "tab:green"}
	x_values = dataframe["index"]

	for species_index, element in enumerate(species):
		axis = axes[species_index]
		for phase in phases:
			column = f"{element}_{phase}"
			plot_series_with_plateau(
				axis=axis,
				x_values=x_values,
				y_values=dataframe[column],
				plateau_indices=plateau_indices,
				label=phase_labels[phase],
				color=colors[phase],
				value_format=".1f",
			)
		axis.set_title(f"{element} atoms")
		axis.set_xlabel("Index")
		axis.set_ylabel("Count")
		if species_index == 0:
			axis.legend(ncol=3)

	for unused_axis_index in range(len(species), num_species_rows * 2):
		axes[unused_axis_index].axis("off")

	final_row_start = num_species_rows * 2
	for property_offset, property_name in enumerate(["lw", "chi"]):
		axis = axes[final_row_start + property_offset]
		plot_series_with_plateau(
			axis=axis,
			x_values=x_values,
			y_values=dataframe[property_name],
			plateau_indices=plateau_indices,
			label=property_name,
			color="tab:red",
			value_format=".3f",
		)
		axis.set_title(property_name)
		axis.set_xlabel("Index")
		axis.set_ylabel(property_name)

	figure.tight_layout(rect=[0, 0, 1, 0.975])
	figure.savefig(output_path, dpi=450)
	plt.show()


def write_plateau_statistics(
	dataframe: pd.DataFrame,
	species: Sequence[str],
	plateau_indices: pd.Index,
	plateau_fraction: float,
	output_path: Path,
) -> None:
	"""Write plateau means and standard deviations to a text file.

	Args:
		dataframe: Summary dataframe.
		species: Species labels to summarize.
		plateau_indices: Row indices used for plateau statistics.
		plateau_fraction: Fraction of final rows used for the plateau.
		output_path: Statistics output path.
	"""
	phases = ["solid", "liquid", "interface"]
	phase_labels = {"solid": "Phase A", "liquid": "Phase B", "interface": "Interface"}
	with output_path.open("w") as file_object:
		file_object.write("Plateau Region Statistics (last {:.0f}% of data)\n".format(plateau_fraction * 100))
		file_object.write("{:<20} {:>10} {:>10}\n".format("Variable", "Mean", "Std Dev"))
		file_object.write("-" * 45 + "\n")
		for element in species:
			for phase in phases:
				column = f"{element}_{phase}"
				label = f"{element}_{phase_labels[phase].replace(' ', '_')}"
				plateau_values = dataframe[column].iloc[plateau_indices]
				file_object.write(
					"{:<20} {:>10.3f} {:>10.3f}\n".format(
						label,
						plateau_values.mean(),
						plateau_values.std(),
					)
				)
		for property_name in ["lw", "chi"]:
			plateau_values = dataframe[property_name].iloc[plateau_indices]
			file_object.write(
				"{:<20} {:>10.3f} {:>10.3f}\n".format(
					property_name,
					plateau_values.mean(),
					plateau_values.std(),
				)
			)


def main(argv: Sequence[str] | None = None) -> None:
	"""Run the GDS proximity summary plotting workflow."""
	args = parse_arguments(argv)
	input_path = resolve_input_path(args.file)
	output_path = Path(args.output)
	stats_output_path = Path(args.stats_output)

	species = read_species_from_id_header(input_path)
	nw_value = read_nw_from_header(input_path)
	dataframe = read_summary(input_path=input_path, species=species)
	plateau_indices = get_plateau_indices(dataframe=dataframe, plateau_fraction=args.plateau_fraction)

	plot_summary(
		dataframe=dataframe,
		species=species,
		plateau_indices=plateau_indices,
		output_path=output_path,
		input_path=input_path,
		nw_value=nw_value,
	)
	write_plateau_statistics(
		dataframe=dataframe,
		species=species,
		plateau_indices=plateau_indices,
		plateau_fraction=args.plateau_fraction,
		output_path=stats_output_path,
	)

	print(f"Species inferred from header: {', '.join(species)}")
	print(f"nw inferred from header: {nw_value}")
	print(f"Read input file {input_path}")
	print(f"Saved figure to {output_path}")
	print(f"Saved plateau statistics to {stats_output_path}")


if __name__ == "__main__":
	main()
