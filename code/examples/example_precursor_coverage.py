"""
Example: Analyzing Precursor Coverage by DIA Windows

This example demonstrates how to:
1. Check if precursors fall within DIA windows
2. Analyze coverage for a single sample
3. Compare coverage across multiple samples
"""

import sys
import os
sys.path.insert(0, os.path.abspath('..'))

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from diann_collection import DiannCollection
from LCMSmethodAnalysis.parsers.timsmeth.ms_method_collection import MSMethodCollection
from LCMSmethodAnalysis.integrator.precursor_window_analysis import (
    analyze_sample_coverage,
    summarize_coverage,
    compare_coverage_across_samples,
    check_precursor_in_windows
)


def example_single_sample_analysis():
    """Example: Analyze DIA coverage for a single sample."""
    print("=" * 80)
    print("EXAMPLE 1: Single Sample Analysis")
    print("=" * 80)

    # Load collections
    bpscollection = DiannCollection.from_file(
        "/Users/eileen.wang/Desktop/diann/SampleData/BPS/bpscollection.pkl"
    )
    mscollection = MSMethodCollection()
    mscollection.add_methods_from_folder(
        "/Users/eileen.wang/Desktop/diann/SampleData/methods/MS/260130_11AM.zip"
    )

    # Get precursor data
    adata = bpscollection.data['precursor']
    samples = adata.var_names.tolist()

    # Select first sample
    sample_name = samples[0]
    print(f"\nAnalyzing sample: {sample_name}")

    # Get single sample data
    sample_adata = adata[:, sample_name]

    # Get MS method and DIA windows
    # Note: You'll need to map samples to methods first
    # For this example, we'll use a specific method
    method_name = 'DIA011RT60.proteoscape'
    if method_name in mscollection.methods:
        dia_windows = mscollection[method_name].get_dia_windows()

        print(f"Using MS method: {method_name}")
        print(f"Number of DIA windows: {len(dia_windows)}")

        # Analyze coverage
        coverage_df = analyze_sample_coverage(
            sample_adata,
            dia_windows,
            mz_col='Precursor.Calibrated.Mz',
            im_col='Exp.1/K0'
        )

        # Get summary statistics
        summary = summarize_coverage(coverage_df)

        print("\nCoverage Summary:")
        print(f"  Total precursors: {summary['total_precursors']}")
        print(f"  Covered by DIA windows: {summary['covered_precursors']} ({summary['coverage_rate']:.1f}%)")
        print(f"  Not covered: {summary['uncovered_precursors']} ({100 - summary['coverage_rate']:.1f}%)")

        # Show some uncovered precursors
        uncovered = coverage_df[~coverage_df['in_window']]
        if len(uncovered) > 0:
            print(f"\nExample uncovered precursors (first 5):")
            print(uncovered[['mz', 'im', 'distance_to_nearest']].head())

        return coverage_df, summary
    else:
        print(f"Method {method_name} not found in collection")
        return None, None


def example_compare_across_samples():
    """Example: Compare coverage across all samples (requires method mapping)."""
    print("\n" + "=" * 80)
    print("EXAMPLE 2: Compare Coverage Across Samples")
    print("=" * 80)

    # Load collections
    bpscollection = DiannCollection.from_file(
        "/Users/eileen.wang/Desktop/diann/SampleData/BPS/bpscollection.pkl"
    )
    mscollection = MSMethodCollection()
    mscollection.add_methods_from_folder(
        "/Users/eileen.wang/Desktop/diann/SampleData/methods/MS/260130_11AM.zip"
    )

    # Note: This requires 'ms meth' column in adata.var
    # You'll need to run the map_lcms_methods function first
    adata = bpscollection.data['precursor']

    if 'ms meth' in adata.var.columns:
        comparison_df = compare_coverage_across_samples(
            bpscollection,
            mscollection,
            level='precursor',
            ms_method_var='ms meth'
        )

        print("\nCoverage by Sample:")
        print(comparison_df[['sample', 'ms_method', 'coverage_rate', 'total_precursors']])

        # Plot coverage comparison
        plt.figure(figsize=(12, 6))
        sns.barplot(
            data=comparison_df,
            x='sample',
            y='coverage_rate',
            hue='ms_method'
        )
        plt.xticks(rotation=45, ha='right')
        plt.ylabel('Coverage Rate (%)')
        plt.xlabel('Sample')
        plt.title('DIA Window Coverage by Sample')
        plt.tight_layout()
        plt.savefig('coverage_comparison.png', dpi=300)
        print("\nPlot saved as 'coverage_comparison.png'")

        return comparison_df
    else:
        print("\nNote: 'ms meth' column not found in sample metadata.")
        print("Run map_lcms_methods() first to map samples to MS methods.")
        return None


def example_visualize_coverage():
    """Example: Visualize precursor coverage on m/z vs IM plot."""
    print("\n" + "=" * 80)
    print("EXAMPLE 3: Visualize Coverage")
    print("=" * 80)

    # Load collections
    bpscollection = DiannCollection.from_file(
        "/Users/eileen.wang/Desktop/diann/SampleData/BPS/bpscollection.pkl"
    )
    mscollection = MSMethodCollection()
    mscollection.add_methods_from_folder(
        "/Users/eileen.wang/Desktop/diann/SampleData/methods/MS/260130_11AM.zip"
    )

    # Get data
    adata = bpscollection.data['precursor']
    sample_name = adata.var_names[0]
    sample_adata = adata[:, sample_name]

    # Get DIA windows
    method_name = 'DIA011RT60.proteoscape'
    if method_name in mscollection.methods:
        dia_windows = mscollection[method_name].get_dia_windows()

        # Analyze coverage
        coverage_df = analyze_sample_coverage(
            sample_adata,
            dia_windows,
            mz_col='Precursor.Calibrated.Mz',
            im_col='Exp.1/K0'
        )

        # Create visualization
        fig, ax = plt.subplots(figsize=(12, 8))

        # Plot DIA windows
        mscollection.plot_windows(
            [method_name],
            color_by_method=True,
            alpha=0.2,
            show_labels=False,
            ax=ax
        )

        # Plot precursors colored by coverage
        scatter = ax.scatter(
            coverage_df['mz'],
            coverage_df['im'],
            c=coverage_df['in_window'],
            s=10,
            alpha=0.5,
            cmap='RdYlGn',
            label='Precursors'
        )

        # Add colorbar
        cbar = plt.colorbar(scatter, ax=ax)
        cbar.set_label('Covered by DIA Window')
        cbar.set_ticks([0, 1])
        cbar.set_ticklabels(['No', 'Yes'])

        ax.set_xlabel('m/z')
        ax.set_ylabel('1/K0 (Ion Mobility)')
        ax.set_title(f'DIA Window Coverage\nSample: {sample_name}\nMethod: {method_name}')

        plt.tight_layout()
        plt.savefig('precursor_coverage_viz.png', dpi=300)
        print(f"\nVisualization saved as 'precursor_coverage_viz.png'")
        print(f"Green points = covered, Red points = not covered")

        return fig, ax


if __name__ == "__main__":
    # Run examples
    try:
        # Example 1: Single sample
        coverage_df, summary = example_single_sample_analysis()

        # Example 2: Compare across samples (requires method mapping)
        # comparison_df = example_compare_across_samples()

        # Example 3: Visualize
        if coverage_df is not None:
            example_visualize_coverage()

    except FileNotFoundError as e:
        print(f"\nError: {e}")
        print("\nMake sure to update the file paths in this script to match your data location.")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
