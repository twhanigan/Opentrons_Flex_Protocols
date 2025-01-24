from opentrons import protocol_api
from opentrons.protocol_api import SINGLE

metadata = {
    'protocolName': 'Mycoplasma Detection PCR Protocol',
    'author': 'Assistant',
    'description': 'Automated PCR setup and gel preparation for Mycoplasma detection.',
}

requirements = {
    "robotType": "Flex",
    "apiLevel": "2.21"
}

def run(protocol: protocol_api.ProtocolContext):

    # Load modules
    heater_shaker = protocol.load_module('heaterShakerModuleV1', 'D1')
    thermocycler = protocol.load_module('thermocyclerModuleV2')
    temp_module = protocol.load_module('temperature module gen2', 'C1')
    mag_block = protocol.load_module('magneticBlockV1', 'D2')
    chute = protocol.load_waste_chute()

    # Load labware
    pcr_plate = thermocycler.load_labware('nest_96_wellplate_100ul_pcr_full_skirt')
    temp_adapter = temp_module.load_labware('opentrons_24_aluminumblock_nest_1.5ml_screwcap')
    tips_50 = protocol.load_labware('opentrons_flex_96_tiprack_50ul', 'A2')

    # Load pipettes
    p50_multi = protocol.load_instrument('flex_8channel_50', 'left') #, tip_racks=[tips_50]
    p1000_multi = protocol.load_instrument('flex_8channel_1000', 'right') #, tip_racks=[tips_200]

    #Configure the p50 pipette to use single tip NOTE: this resets the pipettes tip racks!
    p50_multi.configure_nozzle_layout(style=SINGLE, start="A1",tip_racks=[tips_50])

    # Prompt user for the number of samples
    num_samples = int(input("Enter the number of samples to process (including controls): "))

    # Assign sample locations dynamically
    sample_locations = temp_adapter.rows_by_name()['B'][:num_samples]

    # Define reagents and volumes
    mastermix = temp_adapter['A1']  # BlasTaq 2X PCR MasterMix
    primer_mix = temp_adapter['A2']
    nuclease_free_water = temp_adapter['A3']
    positive_control = temp_adapter['A4']
    ntc = temp_adapter['A5']

    #Add the positive control and no template control to the number of sampesl
    numtotalSamples = num_samples + 2

    reaction_vol = 25
    mastermix_vol = 12.5
    primer_vol = 1
    sample_vol = 2.5

    # Step 1: Distribute mastermix and primer mix into PCR plate starting at row B1:
    #for well in pcr_plate.wells()[:8]:  # Adjust as needed for the number of reactions
    p50_single.distribute(mastermix_vol, mastermix, [well for well in pcr_plate.wells()[:numtotalSamples]], new_tip='once')# Adjust as needed for the number of reactions
    p50_single.distribute(primer_vol, primer_mix, [well for well in pcr_plate.wells()[:numtotalSamples]], new_tip='once')

    # Step 2: Add test sample, positive control, and NTC to PCR plate
    samples = [sample_locations, positive_control, ntc]
    for sample, well in zip(samples, pcr_plate.wells()[:numtotalSamples]):
        p50_single.pick_up_tip()
        p50_single.transfer(sample_vol, sample, well, new_tip='never')
        p50_single.transfer(
            reaction_vol - (mastermix_vol + primer_vol + sample_vol),
            nuclease_free_water,
            well,
            new_tip='never'
        )
        p50_single.mix(3, 20, well)
        p50_single.drop_tip()

    # Step 3: Run thermocycling conditions
    thermocycler.close_lid()
    thermocycler.set_lid_temperature(105)
    thermocycler.set_block_temperature(4, hold_time_minutes=1)

    thermocycler.execute_profile(
        steps=[
            {'temperature': 95, 'hold_time_seconds': 180},  # Initial Denaturation
        ] + [
            {
                'temperature': 95, 'hold_time_seconds': 15
            },  # Denaturation
            {
                'temperature': 55, 'hold_time_seconds': 15
            },  # Annealing
            {
                'temperature': 72, 'hold_time_seconds': 15
            }   # Extension
        ] * 35,  # 35 cycles
        repetitions=1
    )

    thermocycler.set_block_temperature(72, hold_time_minutes=1)  # Final Extension
    thermocycler.set_block_temperature(4)  # Hold at 4°C
    thermocycler.open_lid()

    # Step 4: Gel preparation and loading (manual step for now)
    protocol.comment("After PCR, analyze products on a 2% agarose gel stained with ethidium bromide or SafeView.")