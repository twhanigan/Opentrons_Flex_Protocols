    # Enter the number of samples 
num_samples = 8
# assign sample locations dynamically
sample_locations = []
for i in range(num_samples):
    if i < 6:  # B1 to B6
        sample_locations.append(f'B{i + 1}')
    elif i < 12:  # C1 to C6
        sample_locations.append(f'C{i - 5}')
    elif i < 18:  # D1 to D6
        sample_locations.append(f'D{i - 11}')
    elif i < 23:
        sample_locations.append(f'A{i - 16}')  # Stop if we exceed the number of available rows/columns
    else:
         print('Too many samples')
    # Define reagents and volumes
mastermix = temp_adapter['A1']  # BlasTaq 2X PCR MasterMix
primer_mix = temp_adapter['A2']
nuclease_free_water = temp_adapter['A3']
positive_control = temp_adapter['A4']
ntc = temp_adapter['A5']
samples = temp_adapter[sample_locations]
#Add the positive control and no template control to the number of sampesl
numtotalSamples = num_samples + 2

reaction_vol = 25
mastermix_vol = 12.5
primer_vol = 1
sample_vol = 2.5

#Configure the p50 pipette to use single tip NOTE: this resets the pipettes tip racks!
p50_multi.configure_nozzle_layout(style=SINGLE, start="A1",tip_racks=[partial_50])
    
# Step 1: Distribute mastermix and primer mix into PCR plate starting at row B1:
p50_multi.distribute(mastermix_vol, mastermix, [well for well in pcr_plate.wells()[:numtotalSamples]], new_tip='once')# Adjust as needed for the number of reactions
p50_multi.distribute(primer_vol, primer_mix, [well for well in pcr_plate.wells()[:numtotalSamples]], new_tip='once')

# Step 2: Add test sample, positive control, and NTC to PCR plate
samples = [sample_locations, positive_control, ntc]