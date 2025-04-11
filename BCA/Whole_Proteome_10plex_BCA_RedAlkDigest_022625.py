from opentrons import protocol_api
from opentrons.protocol_api import SINGLE, ALL
import pandas as pd
import numpy as np
#import matplotlib.pyplot as plt
import subprocess
from pathlib import Path
import datetime
import time

metadata = {
    'protocolName': 'TMT-labeled whole proteome sample preparation',
    'author': 'Assistant',
    'description': 'BCA assay and sample protein normalization (<20 Samples), reduction/alkylation and SP3 sample cleanup, trypsin digestion and on bead TMT reaction.'
}

requirements = {
    "robotType": "Flex",
    "apiLevel": "2.21"
}

def run(protocol: protocol_api.ProtocolContext):
    #######################################################################################
    # The necessary amounts of each BSA standard = 1, lysis buffer = 600 (# samples
    #BSA Standard = A1
    #Lysis Buffer = A2
    #Biotin = A3
    #CuSO4 = A4
    #TBTA = A5
    #TCEP = A6
    #Sampes Row B
    #excess lysis buffer goes in falcon tube rack in C4

    protocol.comment(
        "Place BSA Standard in A1, Lysis buffer in A2, samples in row B-C, empty tube in C5, biotin in C6, cuso4 in D4, tbta in D5, tcep in D6")
    protocol.comment("Running the BCA assay")
    
    num_samples = 10 #change this to the number of samples you need to run. The maximum is 18.
    # Change these if not using 96-well
    num_rows = 8  # A-H
    num_replicates = 3  # the number of replicates

    #Start recording the video
    video_output_file = 'BCA_Assay_012425.mp4'
    device_index = "<video2>"
    duration = 200
    video_process = subprocess.Popen(["python3", "/var/lib/jupyter/notebooks/record_video.py"])

    # Load modules
    heater_shaker = protocol.load_module('heaterShakerModuleV1', 'D1')
    thermocycler = protocol.load_module('thermocyclerModuleV2')
    temp_module = protocol.load_module('temperature module gen2', 'C1')
    mag_block = protocol.load_module('magneticBlockV1', 'D2')
    chute = protocol.load_waste_chute()

    # Load adapters
    hs_adapter = heater_shaker.load_adapter('opentrons_universal_flat_adapter')
    temp_adapter = temp_module.load_labware('opentrons_24_aluminumblock_nest_1.5ml_screwcap')
    epp_rack = protocol.load_labware('opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap', location=protocol_api.OFF_DECK)

    #set the heater_shaker temp to 60C
    heater_shaker.set_and_wait_for_temperature(37)

    #set the temp module to 0c
    temp_module.set_temperature(celsius=10)
    
    # Load labware
    tips_50 = protocol.load_labware('opentrons_flex_96_filtertiprack_50ul', 'A4')
    partial_50 = protocol.load_labware(load_name="opentrons_flex_96_filtertiprack_50ul",location="A3")
    tips_200 = protocol.load_labware('opentrons_flex_96_filtertiprack_200ul', 'B4')
    partial_200 = protocol.load_labware(load_name="opentrons_flex_96_filtertiprack_200ul",location="B3")
    plate1 = protocol.load_labware('corning_96_wellplate_360ul_flat', 'A2')
    plate2 = protocol.load_labware('corning_96_wellplate_360ul_flat', 'B2')
    reservoir = protocol.load_labware('nest_12_reservoir_15ml', 'C2')
    
    # load the liquids to the tube racks and reservoirs
    # Define all liquids used in the protocol with unique colors
    bsa_standard = protocol.define_liquid(name='BSA Standard', display_color="#704848")  # Brown
    lysis_buffer = protocol.define_liquid(name='Lysis Buffer', display_color="#FF0000")  # Red
    biotin_azide = protocol.define_liquid(name='Biotin Azide', display_color="#00AA00")  # Green
    copper_sulfate = protocol.define_liquid(name='CuSO4', display_color="#0000FF")  # Blue
    tbta = protocol.define_liquid(name='TBTA', display_color="#800080")  # Purple
    tcep = protocol.define_liquid(name='TCEP', display_color="#FF8C00")  # Orange
    excess_lysis = protocol.define_liquid(name='Excess Lysis Buffer', display_color="#FFC0CB")  # Pink
    epps_urea = protocol.define_liquid(name='2M Urea in EPPS', display_color="#8B4513")  # SaddleBrown
    ethanol = protocol.define_liquid(name='80% Ethanol', display_color="#4682B4")  # SteelBlue
    trypsin = protocol.define_liquid(name='Trypsin in EPPS', display_color="#FFD700")  # Gold
    cacl2 = protocol.define_liquid(name='CaCl2', display_color="#32CD32")  # LimeGreen

    # 24-tube rack (A2, used for various reagents)
    epp_rack['B1'].load_liquid(liquid=lysis_buffer, volume=10000)  # Additional lysis buffer for SP3
    epp_rack['C1'].load_liquid(liquid=tcep, volume=1000)  # TCEP
    epp_rack['C2'].load_liquid(liquid=tbta, volume=1000)  # TBTA
    epp_rack['C3'].load_liquid(liquid=copper_sulfate, volume=1000)  # CuSO4
    epp_rack['C4'].load_liquid(liquid=epps_urea, volume=5000)  # 2M Urea in EPPS

    # Reservoir assignments for washes and digestion
    reservoir['A7'].load_liquid(liquid=excess_lysis, volume=20000)  # Excess lysis buffer
    reservoir['A9'].load_liquid(liquid=ethanol, volume=50000)  # 80% Ethanol
    reservoir['A10'].load_liquid(liquid=ethanol, volume=50000)  # 80% Ethanol for washes
    reservoir['A12'].load_liquid(liquid=epps_urea, volume=20000)  # 2M Urea in EPPS

    # Trypsin and CaCl2 for digestion
    temp_adapter['D5'].load_liquid(liquid=cacl2, volume=500)  # CaCl2
    temp_adapter['D6'].load_liquid(liquid=trypsin, volume=500)  # Trypsin in EPPS 

    # Load pipettes
    p50_multi = protocol.load_instrument('flex_8channel_50', 'left') #, tip_racks=[tips_50]
    p1000_multi = protocol.load_instrument('flex_8channel_1000', 'right') #, tip_racks=[tips_200]

    #Configure the p1000 pipette to use single tip NOTE: this resets the pipettes tip racks!
    p1000_multi.configure_nozzle_layout(style=SINGLE, start="A1",tip_racks=[partial_200])

    # Steps 1: Add lysis buffer to column 1 of plate1. 
    p1000_multi.distribute(50, 
         temp_adapter['A2'],
         plate1.columns('1'),
         rate = 0.35,
         delay = 2,
         new_tip='once')

    # Step 2: move the 200uL partial tips to D4 and then the 50 uL partial tips to B3
    protocol.move_labware(labware=partial_200, new_location="D4", use_gripper=True)
    protocol.move_labware(labware=partial_50, new_location="B3", use_gripper=True)

    #Step 3: Configure the p50 pipette to use single tip NOTE: this resets the pipettes tip racks!
    p50_multi.configure_nozzle_layout(style=SINGLE, start="A1",tip_racks=[partial_50])

    # Step 4: Transfer BSA standard (20 mg/ml) to first well of column 1
    p50_multi.transfer(50,
        temp_adapter['A1'],
        plate1['A1'],
        rate = 0.35,
        delay = 2,
        mix_after=(3, 40),
        new_tip='once')

    # Step 5: Perform serial dilution down column 1
    rows = ['A','B', 'C', 'D', 'E', 'F', 'G']
    p50_multi.pick_up_tip()
    for source, dest in zip(rows[:-1], rows[1:]):
        p50_multi.transfer(50,
                         plate1[f'{source}1'],
                         plate1[f'{dest}1'],
                         rate = 0.5,
                         mix_after=(3, 40),
                         new_tip='never', 
                         disposal_vol=0)

    # Step 6: remove excess standard from well G
    p50_multi.aspirate(50,plate1['G1'])
    p50_multi.drop_tip()

    # assign sample locations dynamically
    sample_locations = []
    for i in range(num_samples):
        if i < 6:  # B1 to B6
            sample_locations.append(f'B{i + 1}')
        elif i < 12:  # C1 to C6
            sample_locations.append(f'C{i - 5}')
        elif i < 18:  # D1 to D6
            sample_locations.append(f'D{i - 11}')
        else:
            break  # Stop if we exceed the number of available rows/columns

    #print the locations of the samples
    print("Sample Locations:", sample_locations)

    # Predefined list of letters A-H
    row = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']

    # Create a list of rows that repeats based on num_samples
    rows = [row[i % len(row)] for i in range(num_samples)]

    # Create a dynamic sample map based on the assigned sample locations
    sample_map = list(map(lambda i,j :(i,j), rows, sample_locations))

    # Print the dynamic sample map for verification
    print("Dynamic Sample Map:", sample_map)

    # Iterate over the sample_map list
    for index, (row, tube) in enumerate(sample_map):
        if index < 8:
            base_column = 4 + (index // 8)  # This will determine the starting column for each row
        elif index< 16:
            base_column = 6 + (index // 8)
        else:
            base_column = 8 + (index //8)

        # Prepare destination wells
        destination_wells = [f'{row}{base_column + (i % 3)}' for i in range(3)]  # Generate wells like A4, A5, A6 or B4, B5, B6, etc.
        print("Distributing from " + tube + " to wells: ", destination_wells)
        
        #Transfer the samples onto plate 2
        p50_multi.distribute(
            10,
            temp_adapter[tube],
            [plate2[i] for i in destination_wells],
            rate = 0.5)  # Distributing to three consecutive columns

    # Step 8: move the 50uL complete tips to A3
    protocol.move_labware(labware=tips_50, new_location="A3", use_gripper=True)

    #Step 9: Load the p50 with full tip rack
    p50_multi.configure_nozzle_layout(style=ALL, tip_racks=[tips_50]) #, 

    #Step 10: Pipette triplicate of controls from plate1 column 1 to plate2 columns 1,2,3 
    p50_multi.distribute(10, plate1['A1'], [plate2[f'A{i}'] for i in range(1, 4)])

    # Step 11: move the 50 uL partial tips to C3 and the 200uL complete tips to B3
    protocol.move_labware(labware=partial_50, new_location="C4", use_gripper=True)
    protocol.move_labware(labware=tips_200, new_location="B3", use_gripper=True)

    #Step 12: Load the p1000 with full tip rack
    p1000_multi.configure_nozzle_layout(style=ALL, tip_racks=[tips_200]) #,

    # Step 13: Add reagent A
    p1000_multi.distribute(75,
                        reservoir['A1'],
                        plate2.wells(),
                        new_tip='once')

    # Step 14: Add reagent B
    p1000_multi.distribute(72,
                        reservoir['A3'],
                        plate2.wells(),
                        new_tip='once')

    # Step 15: Add reagent c
    p50_multi.distribute(3,
                        reservoir['A5'],
                        plate2.wells(),
                        new_tip='once')

    #Step 16: move plate 2 to the heater shaker and incubate at 37c
    heater_shaker.open_labware_latch()
    protocol.move_labware(labware=plate2, new_location=hs_adapter,use_gripper=True)
    heater_shaker.close_labware_latch()
    heater_shaker.set_and_wait_for_shake_speed(500)
    protocol.delay(minutes=5)

    #Step 17 deactivate heater shaker and temp modules
    heater_shaker.deactivate_shaker()
    heater_shaker.deactivate_heater()
    heater_shaker.open_labware_latch()
    #temp_module.deactivate()

    #######################################################################################
    # Tell the user to load BCA assay data
    protocol.comment("Place BCA assay absorbance data in /var/lib/jupyter/notebooks/TWH, load new deep well plate into hs_adapter (where BCA plate was), and new tube rack into A2 (with click mix, beads and TCEP/IAA)")
    
    #define the target protein concentration for the normalized samples and final volume in mL
    target_concentration = 1
    final_volume = 0.440
    final_volume_ul = final_volume*1000

    # Pause the protocol until the user loads the file to /var/lib/jupyter/notebooks
    protocol.pause()

    # Tell user the protocol started
    protocol.comment("Running Protein Normalization")

    # Tell the robot that new labware will be placed onto the deck
    protocol.move_labware(labware=plate1, new_location=protocol_api.OFF_DECK)
    protocol.move_labware(labware=plate2, new_location=protocol_api.OFF_DECK)

    # Load the new labware
    plate3 = protocol.load_labware('thermoscientificnunc_96_wellplate_2000ul', location='B2')  #location='hs_adapter' New deep well plate for final samples
    protocol.move_labware(labware=epp_rack, new_location="A2")
    excess_lysis = protocol.define_liquid(name='excess_lysis', display_color="#FF0077")
    
    #create wells on the new 96-deep well plate
    rows = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
    destination_wells  = [f'{rows[i % 8]}{(i // 8)+ 1}' for i in range(num_samples)]

    #Add some initial lysis buffer to all sample wells
    p1000_multi.distribute(final_volume_ul/2, reservoir['A7'], [plate3[i] for i in destination_wells], rate=0.5, new_tip='once')

    # move the complete 200uL to A4 and then the partial 200 uL tips to B3
    protocol.move_labware(labware=tips_200, new_location="A4", use_gripper=True)
    protocol.move_labware(labware=partial_200, new_location="B3", use_gripper=True)
    
    #Configure the p50 pipette to use single tip NOTE: this resets the pipettes tip racks!
    p1000_multi.configure_nozzle_layout(style=SINGLE, start="A1",tip_racks=[partial_200])

    # Define the directory path
    directory = Path("/var/lib/jupyter/notebooks/TWH/")

    # Get today's date in YYMMDD format
    today_date = datetime.date.today().strftime("%y%m%d")

    find_file = subprocess.Popen(['python3',"/var/lib/jupyter/notebooks/wait_for_file.py"],stdout=subprocess.PIPE,text=True)
    stdout, stderr = find_file.communicate()

    if stderr:
        raise ValueError(f"Error while waiting for file: {stderr}")

    # Extract the file path from the output
    file_path = stdout.splitlines()[1]
    if not file_path:
        raise ValueError("No file path returned by wait_for_file.py")

    protocol.comment(f"Successfully loaded: {file_path}")
    # Read the data file
    df = pd.read_excel(file_path, header=5, nrows=8, usecols="C:N")

    # Create a list of well names (A1 to H12)
    well_names = [f"{row}{col}" for col in range(1, 13) for row in "ABCDEFGH"]

    # Flatten the absorbance values into a single list
    absorbance_values = df.values.flatten()

    # Create the DataFrame
    initial_df = pd.DataFrame({'Well': well_names, 'Absorbance': absorbance_values})

    # Process data for normalization
    samples, replicate_1, replicate_2, replicate_3 = [], [], [], []
    sample_index = 1
    for col_offset in range(0, 12, 3):  # Iterate by column groups (triplets)
        for row_offset in range(8):  # Iterate row-wise for each sample
            start = row_offset * 12 + col_offset  # Starting index for the sample
            if start + 2 < len(initial_df):
                samples.append(f"Sample {sample_index}")
                replicate_1.append(initial_df.iloc[start]['Absorbance'])
                replicate_2.append(initial_df.iloc[start + 1]['Absorbance'])
                replicate_3.append(initial_df.iloc[start + 2]['Absorbance'])
                sample_index += 1

    final_df = pd.DataFrame({
        'Sample': samples,
        'Replicate 1': replicate_1,
        'Replicate 2': replicate_2,
        'Replicate 3': replicate_3
    })

    samples_1_to_8 = final_df.iloc[:8]
    samples_1_to_8['Mean Absorbance'] = samples_1_to_8[['Replicate 1', 'Replicate 2', 'Replicate 3']].mean(axis=1)
    protein_concentrations = [10, 5, 2.5, 1.25, 0.625, 0.3125, 0.15625, 0]
    samples_1_to_8['Protein Concentration (mg/mL)'] = protein_concentrations

    slope, intercept = np.polyfit(samples_1_to_8['Protein Concentration (mg/mL)'], samples_1_to_8['Mean Absorbance'], 1)
    y_pred = slope * samples_1_to_8['Protein Concentration (mg/mL)'] + intercept
    ss_res = np.sum((samples_1_to_8['Mean Absorbance'] - y_pred) ** 2)
    ss_tot = np.sum((samples_1_to_8['Mean Absorbance'] - np.mean(samples_1_to_8['Mean Absorbance'])) ** 2)
    r_squared = 1 - (ss_res / ss_tot)

    unknown_samples = final_df.iloc[8:8 + num_samples]
    unknown_samples['Mean Absorbance'] = unknown_samples[['Replicate 1', 'Replicate 2', 'Replicate 3']].mean(axis=1)
    unknown_samples['Protein Concentration (mg/mL)'] = (unknown_samples['Mean Absorbance'] - intercept) / slope
    
    unknown_samples['Sample Volume (mL)'] = (target_concentration * final_volume) / unknown_samples['Protein Concentration (mg/mL)']
    unknown_samples['Diluent Volume (mL)'] = final_volume - unknown_samples['Sample Volume (mL)']
    unknown_samples.loc[unknown_samples['Sample Volume (mL)'] > final_volume, ['Sample Volume (mL)', 'Diluent Volume (mL)']] = [final_volume, 0]
    protocol.comment("\nNormalized Unknown Samples (to 1 mg/mL in 500 µL):")
    print(unknown_samples[['Sample', 'Protein Concentration (mg/mL)', 'Sample Volume (mL)', 'Diluent Volume (mL)']])

    normalized_samples = unknown_samples[['Sample', 'Protein Concentration (mg/mL)', 'Sample Volume (mL)', 'Diluent Volume (mL)']].reset_index().drop(columns='index')

    # Add the samples and the rest of the lysis buffer to plate 3
    for i, row in normalized_samples.iterrows():
        source_well = sample_locations[i]
        normalized_volume = row['Sample Volume (mL)']
        diluent_volume = (final_volume_ul/2) - normalized_volume
        destination_well = destination_wells[i]
        p1000_multi.transfer(normalized_volume, temp_adapter[source_well], plate3[destination_well], rate=0.5, new_tip='once')
        p1000_multi.transfer(diluent_volume, reservoir['A7'], plate3[destination_well], rate=0.5, new_tip='once')
    
    #########################################################################################
    protocol.comment("Reducing Alkylating and Digesting")

    #trick heater_shaker into using 96-well plates
    protocol.move_labware(labware=hs_adapter, new_location=protocol_api.OFF_DECK, use_gripper=False)
    plate_adapter = heater_shaker.load_adapter('Opentrons 96 Deep Well Heater-Shaker Adapter')

    # mix the sp3 beads to homogenize
    p1000_multi.pick_up_tip()
    p1000_multi.mix(4, 200, epp_rack['B1'])
    p1000_multi.drop_tip()

    # transfer the sp3 beads for protein precipitation
    p1000_multi.distribute(60, epp_rack['B1'], [plate3[i] for i in destination_wells])
    
    #Remember the volume added to the samples
    added_vol = 0
    added_vol = added_vol + 60

    # incubate beads with shaking for 5 minutes
    heater_shaker.close_labware_latch()
    heater_shaker.set_and_wait_for_shake_speed(1000)
    protocol.delay(minutes=5)

    # move the partial 200uL to B4 and then the partial 200 uL tips to B3
    protocol.move_labware(labware=partial_200, new_location="B4", use_gripper=True)
    protocol.move_labware(labware=tips_200, new_location="B3", use_gripper=True)
    
    #Configure the p50 pipette to use All tips 
    p1000_multi.configure_nozzle_layout(style=ALL, tip_racks=[tips_200])

    # Determine number of full columns to fill
    num_full_columns = (num_samples + 7) // 8  # Round up to ensure all samples are covered

    # Get the destination wells as full columns
    destination_columns = plate3.columns()[:num_full_columns]

    # Convert columns to top-row wells (e.g., ['A1', 'A2', ..., 'A12'])
    destination_wells_col = [col[0] for col in destination_columns]  # Only use top row for multi-channel pipette

    # Add EtOH to the sample columns and use air gap for volatility
    p1000_multi.distribute(600, reservoir['A9'], destination_wells_col, new_tip='once',air_gap=10)

    #Remember the volume added to the samples
    added_vol = added_vol + 600

    # incubate ethanol with shaking for 5 minutes
    heater_shaker.set_and_wait_for_shake_speed(1000)
    protocol.delay(minutes=5)
    heater_shaker.deactivate_shaker()
    
    # Move samples to the magnet
    heater_shaker.open_labware_latch()
    protocol.move_labware(labware=plate3, new_location=mag_block, use_gripper=True)
    protocol.delay(minutes=3)

    # Remove the EtOH from the beads leaving 200 uL in the bottom
    p1000_multi.consolidate(900, [well.bottom(z=0.2) for well in destination_wells_col], reservoir['A11'], rate=0.5, new_tip='once')
    #Remember the volume added to the samples
    added_vol = added_vol -900

    # Remove remaineder of EtOH and Add 80% EtOH and wash the beads three times with 200 uL 80% EtOH
    for i in range(3):
        p1000_multi.consolidate(200, [well.bottom(z=0.2) for well in destination_wells_col], reservoir['A11'], rate = 0.35, new_tip='once')
        protocol.move_labware(labware=plate3, new_location=plate_adapter, use_gripper=True)
        p1000_multi.distribute(200, reservoir['A10'], destination_wells_col, mix_after=(3, 150), new_tip='once')
        if i<2:
            protocol.move_labware(labware=plate3, new_location=mag_block, use_gripper=True)
        else:
            protocol.move_labware(labware=plate3, new_location=mag_block, use_gripper=True)
            p1000_multi.consolidate(200, [well.bottom(z=0.2) for well in destination_wells_col], reservoir['A11'], rate = 0.35, new_tip='once')
    
    # resuspend in 2 M urea in EPPS with 0.2% SDS and move to shaker
    protocol.move_labware(labware=plate3, new_location=plate_adapter, use_gripper=True)
    p1000_multi.distribute(200, reservoir['A12'], destination_wells_col, mix_after=(3, 150), new_tip='once')
   
    #Remember the volume added to the samples
    added_vol = added_vol + 200

    #set the heater_shaker temp to 37 c for reduce
    heater_shaker.set_and_wait_for_temperature(37)

    # move the partial 200uL to A4 and then the partial 200 uL tips to B3
    protocol.move_labware(labware=tips_200, new_location="A4", use_gripper=True)
    protocol.move_labware(labware=partial_200, new_location="B3", use_gripper=True)

    #Configure the p50 pipette to use single tip NOTE: this resets the pipettes tip racks!
    p1000_multi.configure_nozzle_layout(style=SINGLE, start="A1",tip_racks=[partial_200])

    #Pipette mix K2CO3, and TCEP and transfer to samples
    Redu_mix = num_samples*50*1.2/2
    p1000_multi.transfer(Redu_mix, epp_rack['C1'], epp_rack['C4'], new_tip='always')
    p1000_multi.transfer(Redu_mix, epp_rack['C2'], epp_rack['C4'], new_tip='always')
    p1000_multi.distribute(50, epp_rack['C4'], [plate3[i] for i in destination_wells], new_tip='always')
    
    #Remember the volume added to the samples
    added_vol = added_vol + 50

    # Reduce for 30 minutes
    heater_shaker.close_labware_latch()
    heater_shaker.set_and_wait_for_shake_speed(1000)
    protocol.delay(minutes=30)
    heater_shaker.deactivate_shaker()

    # add IAA and alkylate for 30 minutes
    p1000_multi.distribute(70, epp_rack['C3'], [plate3[i] for i in destination_wells], new_tip='always')
    heater_shaker.set_and_wait_for_shake_speed(1000)
    protocol.delay(minutes=30)
    heater_shaker.deactivate_shaker()

    #Remember the volume added to the samples
    added_vol = added_vol +70

    # move the partial 200uL to A4 and then the partial 200 uL tips to B3
    protocol.move_labware(labware=partial_200, new_location="B4", use_gripper=True)
    protocol.move_labware(labware=tips_200, new_location="B3", use_gripper=True)
    
    #Configure the p100 pipette to use All tips
    p1000_multi.configure_nozzle_layout(style=ALL, tip_racks=[tips_200])

    # Add EtOH and wash beads 3 times again
    p1000_multi.distribute(400, reservoir['A10'], destination_wells_col, new_tip='once')
    
    #Remember the volume added to the samples
    added_vol = added_vol +400

    # Incubate with EtOH for 5-10 minutes
    heater_shaker.set_and_wait_for_shake_speed(1000)
    protocol.delay(minutes=5)
    heater_shaker.deactivate_shaker()

    # Move samples to the magnet and remove EtOH
    heater_shaker.open_labware_latch()
    protocol.move_labware(labware=plate3, new_location=mag_block, use_gripper=True)
    protocol.delay(minutes=3)
    p1000_multi.consolidate(520, [well.bottom(z=0.2) for well in destination_wells_col], reservoir['A11'], rate = 0.5, new_tip='once')
    
    #Remember the volume added to the samples
    added_vol = added_vol -520

    # Wash the beads 3 times with 80% EtoH
    for i in range(3):
        p1000_multi.consolidate(200, [well.bottom(z=0.2) for well in destination_wells_col], reservoir['A11'], rate = 0.35, new_tip='once')
        protocol.move_labware(labware=plate3, new_location=plate_adapter, use_gripper=True)
        p1000_multi.distribute(200, reservoir['A10'], [well.bottom(z=0.2) for well in destination_wells_col], mix_after=(3, 150), new_tip='once')
        if i<2:
            protocol.move_labware(labware=plate3, new_location=mag_block, use_gripper=True)
        else:
            protocol.move_labware(labware=plate3, new_location=mag_block, use_gripper=True)
            p1000_multi.consolidate(200, [well.bottom(z=0.2) for well in destination_wells_col], reservoir['A11'], rate = 0.35, new_tip='once')
    
    # move plate3 to the heater shaker and resuspend in 2 M urea in EPPS
    protocol.move_labware(labware=plate3, new_location=plate_adapter, use_gripper=True)
    p1000_multi.distribute(147.5, reservoir['A12'], destination_wells_col, mix_after=(3, 150), new_tip='once')
    
    #Remember the volume added to the samples
    added_vol = added_vol + 147.5

    # move the partial 200uL to A4 and then the partial 200 uL tips to B3
    protocol.move_labware(labware=tips_200, new_location="A4", use_gripper=True)
    protocol.move_labware(labware=partial_50, new_location="B3", use_gripper=True)

    #Configure the p50 pipette to use single tip NOTE: this resets the pipettes tip racks!
    p50_multi.configure_nozzle_layout(style=SINGLE, start="A1",tip_racks=[partial_50])

    # Add CaCl2, trypsin in epps, and move to shaker
    p50_multi.distribute(2.5, temp_adapter['D5'], [plate3[i] for i in destination_wells], new_tip='once')
    p50_multi.distribute(50, temp_adapter['D6'], [plate3[i] for i in destination_wells], new_tip='once')

    #Remember the volume added to the samples
    added_vol = added_vol + 2.5 + 50

    # Digest overnight
    heater_shaker.close_labware_latch()
    heater_shaker.set_and_wait_for_shake_speed(1000)
    protocol.delay(minutes=960)
    heater_shaker.deactivate_shaker()
    heater_shaker.open_labware_latch()
    protocol.comment("Samples have been digested")


    # Stop video recording after the main task is completed
    video_process.terminate()