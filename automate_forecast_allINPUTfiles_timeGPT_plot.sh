#!/bin/bash
####
# steps to run swan forecast automatically everyday (for one domain)
# Last modified: 17/09/2026 by @laloyo
####
# STEPS
# 0. choose domain and make input file (this and INPUT.swn file should be done)
echo "choose the domain and make input file (this and INPUT.swn file should be done before hand)"
# Exit on error
set -e

# Deactivate conda and Activate the Python virtual environment
#conda deactivate
source /home/laloyo/environments/utm_env/bin/activate #path to you venv

# DEFINE case and corresponding bc point coords
# TODO: auto
declare -A CASES_LAT CASES_LON
CASES_LAT["alcudia"]=39.82
CASES_LON["alcudia"]=3.204

CASES_LAT["cala_millor"]=39.67
CASES_LON["cala_millor"]=3.5

CASES_LAT["palma"]=39.5
CASES_LON["palma"]=2.65

CASES_LAT["tarragona"]=41.06
CASES_LON["tarragona"]=1.24

# DEFINEE!!!! choose case and utm conversion location
CASE="tarragona"  # Change this for other cases
SWAN_CASE="ca00" # choose case

# DEFINE BASE DIRECTORY!!!!!!!!
BASE_DIR="/home/laloyo/waves-MED/"

# if using timeGPT module, choose the variable you'd like to predict with timeGPT
# options are: Hsig, Tp, Tm1, Tm2. for exact definitions look at SWAN user manual
GPT_target_VAR="Hsig"

# corresponding lot lan for bc point
LAT=${CASES_LAT[$CASE]}
LON=${CASES_LON[$CASE]}

# define directories !!!!!
CASE_DIR="${BASE_DIR}/cases/${CASE}"
TIMEGPT_DIR="${BASE_DIR}/timeGPT/"
VAL_DIR="${BASE_DIR}/scripts/validation"
INPUT_DIR="${CASE_DIR}/input"
# swan files
SWAN_INPUT_FILE="${CASE_DIR}/input_${SWAN_CASE}.swn"
SWAN_RUN_FILE="${CASE_DIR}/swanrun"

# dates (caos because it wasn't working correctly)
TODAY=$(date +%Y%m%d)

DATE_MINUS_2D=$(date -d "$TODAY -2 days" +%Y%m%d)
DATE_MINUS_1D=$(date -d "$TODAY -1 days" +%Y%m%d)
DATE_PLUS_1D=$(date -d "$TODAY +1 day" +%Y%m%d)
DATE_PLUS_2D=$(date -d "$TODAY +2 day" +%Y%m%d)
#echo "$DATE_PLUS_2D"
# Ensure DATE_BASE has hours explicitly set
DATE_MINUS_2D_HH="${DATE_MINUS_2D}00"
DATE_MINUS_1D_HH="${DATE_MINUS_1D}00"

# Get time directory (YYYYMM format from START_DATE)
TIME_DIR=$(date -d "$TODAY" +"%Y%m")
OUTPUT_DIR="${CASE_DIR}/output/${TIME_DIR}"
mkdir -p ${OUTPUT_DIR}

# Debugging output
echo "CASE NAME: $CASE"
echo "swan case num: $SWAN_CASE"
echo "TODAY: $TODAY"

# Define time stamps
TIME_STAMPS=("00" "12")
TIME_STAMPS=("01" "13")

# Print for debugging
echo "TODAY       : $TODAY"
#echo "$DATE_PLUS_1D"
cd $BASE_DIR
# 1. adjust and interpolate bathymetry to INPUT.swn CGRID line: scripts/bathy/interpolate.py
echo "1. intertpolatinnnnn EMODNET bathymetry to domain"
# we move to the corresponding path
cd ./scripts/bathy/
#python3 download_and_interp_EMODNET_withcoastline_angle.py "$CASE" "$SWAN_CASE" "$LAT" "$LON"
echo "coastline must be downloaded from EMODNET before hand, bathymetry is automatically downloaded"
echo "interpolation must be done just once, if you already created bathy_matrix just comment the interpolation part on the script"

# 2. download simar_point data for the fc
echo "2. downloadinn open water wave conditions from PdE"
echo "Remember, defining the lat,lon coordinates on teh script for your case"
cd $BASE_DIR
cd ./scripts/opendap/
python3 save_simar_point_to_TPAR.py "$CASE" "$LAT" "$LON"


cd $BASE_DIR

FILE0="TPAR_HW-${DATE_MINUS_2D}01-${DATE_PLUS_1D}00-B${DATE_MINUS_2D}00-FC_point_${LAT}_${LON}.txt"
FILE1="TPAR_HW-${DATE_MINUS_2D}13-${DATE_PLUS_1D}12-B${DATE_MINUS_2D}12-FC_point_${LAT}_${LON}.txt"
FILE2="TPAR_HW-${DATE_MINUS_1D}01-${DATE_PLUS_2D}00-B${DATE_MINUS_1D}00-FC_point_${LAT}_${LON}.txt"
FILE3="TPAR_HW-${DATE_MINUS_1D}13-${DATE_PLUS_2D}12-B${DATE_MINUS_1D}12-FC_point_${LAT}_${LON}.txt"
# me invento un file que no existe para cuando quiero correr con otro file
FILE4="TPAR_nonexistent.txt"
# Print filenames
echo "$FILE0"
echo "$FILE1"
echo "$FILE2"
echo "$FILE3"

#INPUT_FILES=("$FILE3" "$FILE2" "$FILE1" "$FILE0")
#echo "INPUT_FILES: ${INPUT_FILES[@]}"
#asi priorizamos orden file3,file2,file1,file0
for i in 3 2 1 0; do 
    FILE_VAR="FILE$i"
    FILE="${!FILE_VAR}"  # Esto accede a FILE3, FILE2, etc.
    TPAR_PATH="${INPUT_DIR}/${TIME_DIR}/${FILE}"

    if [[ -f "$TPAR_PATH" ]]; then
        echo "File $FILE exists at $TPAR_PATH"
        SELECTED_INPUT="$TPAR_PATH"
        SELECTED_INDEX=$i
        break
    else
        echo "File $FILE does not exist at $TPAR_PATH."
    fi
done

# If no file is found, exit with an error
if [[ -z "$SELECTED_INPUT" ]]; then
    echo "Error: No valid input file found. Exiting."
    exit 1
fi

echo "Using input file: $SELECTED_INPUT"

BASE_NAME=$(basename "$SELECTED_INPUT")
# Copy the selected file for boundary conditions
BOUNDARIES=("north" "west" "east" "south")
BOUNDARY_LETTERS=("N" "W" "E" "S")

for i in "${!BOUNDARIES[@]}"; do
    BC="${BOUNDARIES[$i]}"
    BC_LETTER="${BOUNDARY_LETTERS[$i]}"

    # Construct the boundary file path
    BOUNDARY_FILE="${INPUT_DIR}/${TIME_DIR}/TPAR_${BC}_$BASE_NAME"
    
    # Copy the file to the boundary condition directory
    cp "$SELECTED_INPUT" "$BOUNDARY_FILE"
    echo "Copying $SELECTED_INPUT for $BC to $BOUNDARY_FILE"
    
    # Adjust boundary conditions in the SWAN input file using sed
    sed -i "s#^BOUN  SIDE ${BC_LETTER} .*#BOUN  SIDE ${BC_LETTER} CON FILE '$BOUNDARY_FILE'#" "$SWAN_INPUT_FILE"
done


# 3.adjust  COMPute NONSTationary line in INPUT.swn file to adjust to eachday fc
SWAN_INPUT_FILE="${CASE_DIR}/input_${SWAN_CASE}.swn"
SWAN_RUN_FILE="${CASE_DIR}/swanrun"
# bathy name
sed -i "s#^READINP   BOTTOM 1 .*#READINP   BOTTOM 1 'bathy/bottom_${SWAN_CASE}_matrix.dat' 1 0 FREE#" "$SWAN_INPUT_FILE"
# compution times
#sed -i "s/^COMPUTE NONSTat .*/COMPUTE NONSTat ${TODAY:0:8}.000000 1 HR ${DATE_PLUS_1D:0:8}.000000/" "$SWAN_INPUT_FILE"
# adjust output names
sed -i "s#^BLOCK 'COMPGRID' NOHEAD .*#BLOCK 'COMPGRID' NOHEAD '${OUTPUT_DIR}/Malla_${SWAN_CASE}_F${SELECTED_INDEX}_${TODAY:0:8}_${DATE_PLUS_1D:0:8}.mat' LAY 3 XP YP DEP HSIGN TM02 RTP DIR OUTPUT ${TODAY:0:8}.000000 1 HR#" "$SWAN_INPUT_FILE"
# we create a variable that saves the main output path to later find the file in timeGPT
SWAN_OUTPUT_FILE="${OUTPUT_DIR}/tableP_${SWAN_CASE}_F${SELECTED_INDEX}_${TODAY:0:8}_${DATE_PLUS_1D:0:8}.txt"
sed -i "s#^TABle 'POINT' HEADER .*#TABle 'POINT' HEADER '$SWAN_OUTPUT_FILE' TIME XP YP DEP HSIGN TM02 RTP DIR OUTPUT ${TODAY:0:8}.000000 1 HR#" "$SWAN_INPUT_FILE"

# we adjust end date time according to avilable file
echo "selected file: $SELECTED_FILE"
echo "index: $SELECTED_INDEX"

case $SELECTED_INDEX in
    0)  # FILE0
        END_DATE="${DATE_PLUS_1D:0:8}.000000"
        ;;
    1)  # FILE1
        END_DATE="${DATE_PLUS_1D:0:8}.120000"
        ;;
    2)  # FILE2
        END_DATE="${DATE_PLUS_2D:0:8}.000000"
        ;;
    3)  # FILE3
        END_DATE="${DATE_PLUS_2D:0:8}.120000"
        ;;
    *)
        echo "Error: Invalid file index."
        exit 1
        ;;
esac

# selected end date:
echo "Running till selected end date: $END_DATE"

# modify end date in INPUT file
sed -i "s/^COMPUTE NONSTat .*/COMPUTE NONSTat ${TODAY:0:8}.000000 1 HR ${END_DATE}/" "$SWAN_INPUT_FILE"

# 4. run swan
sed -i "s#^input=.*#input=input_${SWAN_CASE}#" "${SWAN_RUN_FILE}"
cd $CASE_DIR
echo "before running you must have swanrun and swan.exe correctly compiled in the case directory"
./swanrun
echo "standard forecast finishedd!!"

# TODO add more comments when finishing like case, FILe etc

#echo "The main output then used for timeGPT is in ${SWAN_OUTPUT_FILE}"
# 5. automatize some output plots 
#calculate mareograf wave parameters from series
#cd $VAL_DIR
#python3 download_and_calculate_mareograf_op.py
#plot
#python3 compare_palma_times_automate.py
# we add timeGPT
cd $TIMEGPT_DIR 
echo "remember to add you nixtla key in the TIMEGPT_DIR"
echo "you have to define the variable you want to predict with timeGPT at the start of the file"
echo "options are: Hsig, Tp, Tm1, Tm2. for exact definitions look at SWAN user manual"
python3 ./timeGPT.py "$CASE" "$GPT_target_VAR" "$SWAN_OUTPUT_FILE"
