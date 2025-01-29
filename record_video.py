import time
import imageio.v3 as iio
import imageio.v2 as iid

# call this script in your opentrons protocol to 
#initiate recording a video of the instrument during your run.

def record_video(output_file: str, duration: int, device_index: str = "<video2>"):
    """
    Record video from the flexs camera.

    Args:
        output_file (str): Path to the output video file.
        duration (int): Duration to record (in seconds).
        device_index (str): Camera device (e.g., "<video2>").
    """
    print(f"Recording video to {output_file} for {duration} seconds...")

    # Open the video writer with the desired FPS
    fps = 3  # Adjust FPS as needed
    writer = iid.get_writer(output_file, fps=fps)

    start_time = time.time()
    
    # Capture frames from the camera for the specified duration
    for idx, frame in enumerate(iio.imiter(device_index)):
        # Stop recording after the specified duration
        if time.time() - start_time > duration:
            break

        # Print the current frame index for debugging
        #print(f"Frame {idx}")

        # Write the current frame to the video file
        writer.append_data(frame)

    # Close the writer when done
    writer.close()
    print("Recording completed!")

# Generate a filename with the current date and time
timestamp = time.strftime("%Y%m%d_%H%M%S")  # e.g., "20250125_153045"
output_file = f"/var/lib/jupyter/notebooks/{timestamp}.mp4"

# Record a 10-second video from <video2> (adjust device index as necessary)
record_video(output_file, duration=2100, device_index="<video2>")