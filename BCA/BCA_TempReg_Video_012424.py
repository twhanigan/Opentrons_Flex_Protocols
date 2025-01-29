from opentrons import protocol_api
from opentrons.protocol_api import SINGLE, ALL
#import time
#import sys
#import imageio.v3 as iif
#import imageio.v2 as iid
import subprocess

metadata = {
    'protocolName': 'BSA Assay with Video Recording',
    'author': 'Assistant',
    'description': 'Serial dilution of BSA standard and sample processing. This includes cooling samples to 4c, heating plate to 37c with shaking and recording a video of the whole process. Place BSA Standard in A1, Lysis buffer in A2, change the number of samples and place samples in row B starting at B1. MINIMUM Sample volumen in eppendorf tubes is 40 uL. '
}

requirements = {
    "robotType": "Flex",
    "apiLevel": "2.21"
}

def run(protocol: protocol_api.ProtocolContext):
    #say hello
    protocol.comment("Place BSA Standard in A1, Lysis buffer in A2, and samples in row B")
    
    num_samples = 7 #change this to the number of samples you need to run. The maximum is 18.
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

    #set the heater_shaker temp to 60C
    heater_shaker.set_and_wait_for_temperature(37)

    #set the temp module to 0c
    temp_module.set_temperature(celsius=10)
    
    # Load labware
    tips_50 = protocol.load_labware('opentrons_flex_96_tiprack_50ul', 'A4')
    partial_50 = protocol.load_labware(load_name="opentrons_flex_96_tiprack_50ul",location="A3")
    tips_200 = protocol.load_labware('opentrons_flex_96_tiprack_200ul', 'B4')
    partial_200 = protocol.load_labware(load_name="opentrons_flex_96_tiprack_200ul",location="B3")
    plate1 = protocol.load_labware('corning_96_wellplate_360ul_flat', 'A2')
    plate2 = protocol.load_labware('corning_96_wellplate_360ul_flat', 'B2')
    reservoir = protocol.load_labware('nest_12_reservoir_15ml', 'C2')
    
    # Liquid definitions
    bsa_standard = protocol.define_liquid(name = 'BSA Standard', display_color="#704848",)
    lysis_buffer = protocol.define_liquid(name = 'Lysis Buffer', display_color="#FF0000",)
    sample_liquids = [protocol.define_liquid(name = f'Sample {i + 1}', display_color="#FFA000",) for i in range(num_samples)]

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
    protocol.move_labware(labware=partial_50, new_location="C3", use_gripper=True)
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
                        reservoir['A5'],
                        plate2.wells(),
                        new_tip='once')

    # Step 15: Add reagent c
    p1000_multi.distribute(3,
                        reservoir['A9'],
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
    temp_module.deactivate()

    # Stop video recording after the main task is completed
    video_process.terminate()