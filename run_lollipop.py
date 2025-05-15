"""This scripts executes lollipop by building the wrangeling the input data
    and configurations into foram on the fly.

    requires the command line tools:
    - lollipop
    - xsv
    - gawk
    
"""


##### imports
from pathlib import Path
from tempfile import TemporaryDirectory
import yaml
import shutil
import subprocess 

# load the data
mutation_counts = Path("data/mutation_counts_coverage.csv")
mutation_variant_matrix = Path("data/mutation_variant_matrix.csv")

# set the parameters
bootstraps = 0
bandwidth = 30
regressor = "robust"
regressor_params = {"f_scale": 0.01}
deconv_params = {"min_tol": 1e-3}


#with TemporaryDirectory() as tmpdir:
tmpdir = "tempdir"
# make the temporary directory
tmpdir = Path(tmpdir)
# make the output directory
output_dir = tmpdir / "output"
output_dir.mkdir(parents=True, exist_ok=True)

# make the input directory
input_dir = tmpdir / "input"
input_dir.mkdir(parents=True, exist_ok=True)

# copy the data to the input directory

shutil.copy(mutation_counts, input_dir / mutation_counts.name)
shutil.copy(mutation_variant_matrix, input_dir / mutation_variant_matrix.name)

###########################
# make the variants_config.yaml file yaml
# as
""" variants_pangolin:
"KP.3": "KP.3"
"KP.2": "KP.2"
"LP.8": "LP.8"

"""
# get the variants from the mutation_variant_matrix, i.e. the columns
with open(input_dir / "variants_config.yaml", "w") as f:
    variants = mutation_variant_matrix.read_text().splitlines()[0].split(",")[1:]
    variants_dict = {variant: variant for variant in variants}
    yaml.dump({"variants_pangolin": variants_dict}, f)

############################
#  make the deconv_bootstrap_cowwid.yaml config
"""bootstrap: 0

kernel_params:
bandwidth: 30

regressor: robust
regressor_params:
f_scale: 0.01

deconv_params:
min_tol: 1e-3
"""

with open(input_dir / "deconv_bootstrap_cowwid.yaml", "w") as f:
    deconv_config = {
        "bootstrap": bootstraps,
        "kernel_params": {
            "bandwidth": bandwidth
        },
        "regressor": regressor,
        "regressor_params": regressor_params,
        "deconv_params": deconv_params
    }
    yaml.dump(deconv_config, f)


############################
#  prepare the input data i.e. make the tallymut

# Generate separate "pos"ition and variant "base" columns from the mutation data
gawk_command = [
    "gawk",
    r'BEGIN{FS=","};NR==1{print "pos,base," $0};NR>1{match($1,/[ATGC]?([[:digit:]]+)([ATCG\-])/, ary); print ary[1] "," ary[2] "," $0 }',
    str(input_dir / mutation_variant_matrix.name)
]

# Create output filename with descriptive suffix
matrix_pos_base_file = output_dir / (mutation_variant_matrix.stem + "_pos_base.csv")

try:
    with open(matrix_pos_base_file, "w") as f:
        subprocess.run(gawk_command, check=True, stdout=f, stderr=subprocess.PIPE, text=True)
    print(f"Successfully parsed mutation positions and bases: {matrix_pos_base_file}")
except subprocess.CalledProcessError as e:
    print(f"Error running gawk command: {e}")
    if e.stderr:
        print(e.stderr)
    exit(1)

# # add the  above-update matrix to the mutation counts+coverage table
# xsv join --left mutation  /tmp/mutation_counts_coverage.csv  Mutation /tmp/mutation_variant_matrix2.csv | xsv select sampling_date,count,coverage,frequency,mutation,pos,base,9-  | xsv fmt --out-delimiter '\t'  | sed '1s/sampling_date/date/;1s/coverage/cov/;1s/frequency/frac/' >  /tmp/tallymut.tsv

# Create output filename with descriptive suffix
tallymut_file = output_dir / (mutation_counts.stem + "_tallymut.tsv")

try:
    # First subprocess: xsv join
    join_command = [
        "xsv",
        "join",
        "--left",
        "mutation",
        str(input_dir / mutation_counts.name),
        "Mutation",
        str(matrix_pos_base_file)
    ]
    join_result = subprocess.run(join_command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    # Second subprocess: xsv select
    select_command = [
        "xsv",
        "select",
        "sampling_date,count,coverage,frequency,mutation,pos,base,9-"
    ]
    select_result = subprocess.run(select_command, input=join_result.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)

    # Third subprocess: xsv fmt
    fmt_command = [
        "xsv",
        "fmt",
        "--out-delimiter",
        "\t"
    ]
    fmt_result = subprocess.run(fmt_command, input=select_result.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)

    # Fourth subprocess: sed
    sed_command = [
        "sed",
        "1s/sampling_date/date/;1s/coverage/cov/;1s/frequency/frac/"
    ]
    with open(tallymut_file, "w") as f:
        subprocess.run(sed_command, input=fmt_result.stdout, stdout=f, stderr=subprocess.PIPE, text=True, check=True)
    print(f"Successfully created tally mutation file: {tallymut_file}")

except subprocess.CalledProcessError as e:
    print(f"Error running command: {e}")
    if e.stderr:
        print(e.stderr)
    exit(1)



# # deconvolute
# lollipop deconvolute --output /tmp/deconvolved.csv --out-json /tmp/deconvolved.json -c /tmp/lolli_config.yaml --deconv-config /home/dryak/project/LolliPop/presets/deconv_bootstrap_cowwid.yaml --namefield mutation /tmp/tallymut.tsv 



# run lollipop


# read in the deconvoluted.json file



# print the output

