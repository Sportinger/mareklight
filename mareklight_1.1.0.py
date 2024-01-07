import threading
from PIL import Image
import pystray
from pystray import MenuItem as item
import subprocess
import tkinter as tk
from tkinter import simpledialog
import time
import datetime

current_version = '1.1.0'  # Current version of your app

# Create and hide the root window immediately
root = tk.Tk()
root.withdraw()

PING_INTERVAL = 60  # Time between pings in seconds
update_lock = threading.Lock() 
interval_changed = threading.Event()  # Add this line

def ping_ip(ip_address):
    try:
        # Set creationflags to CREATE_NO_WINDOW to suppress the console window
        process = subprocess.run(["ping", "-n", "1", "-w", "1000", ip_address[0]],
                                 capture_output=True, text=True, encoding='cp850',
                                 timeout=2, creationflags=subprocess.CREATE_NO_WINDOW)
        output = process.stdout
        if "TTL=" in output:
            return True, output
        else:
            return False, output
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        return False, e.output if e.output else ""

def create_image(color):
    # Create an image with given background color
    width = 64
    height = 64
    image = Image.new('RGB', (width, height), color)
    return image

def flash_icon_blue(icon):
    with update_lock:
        original_icon = icon.icon
        icon.icon = create_image('blue')
        time.sleep(0.5)
        icon.icon = original_icon

def update_tray_icon(icon, ip_address, running, last_change):
    last_status = None
    while running[0]:
        flash_icon_blue(icon)
        success, _ = ping_ip(ip_address)
        new_color = 'green' if success else 'red'
        
        current_status = new_color
        if current_status != last_status:
            last_change[0] = datetime.datetime.now()  # Update the last_change timestamp
            last_status = current_status
        
        icon.icon = create_image(new_color)
        icon.update_menu()  # Trigger menu update to reflect new elapsed time
        
        
        # Wait for the interval or until the event is set
        interval_changed.wait(PING_INTERVAL)
        # Clear the event after waking up
        interval_changed.clear()


def set_ip(icon, ip_address, running):
    # Use the hidden root window for the dialog
    new_ip = simpledialog.askstring("Enter IP", "Enter new IP address:", parent=root, initialvalue=ip_address[0])
    if new_ip:
        ip_address[0] = new_ip
        flash_icon_blue(icon)

def update_interval(new_interval):
    global PING_INTERVAL
    PING_INTERVAL = new_interval
    # Set the interval_changed event to notify the update_tray_icon thread
    interval_changed.set()

def create_tray_icon(ip_address, running, last_change):

    def exit_program():
        running[0] = False
        icon.stop()

    interval_menu = pystray.Menu(
        item('1 sec', lambda: update_interval(1)),
        item('10 sec', lambda: update_interval(10)),
        item('1 min', lambda: update_interval(60)),
        item('10 min', lambda: update_interval(600))
    )

    icon = pystray.Icon("mareklight", create_image('red'), "mareklight")
    update_thread = threading.Thread(target=update_tray_icon, args=(icon, ip_address, running, last_change))
    update_thread.start()

    refresh_thread = threading.Thread(target=refresh_menu, args=(icon, ip_address, last_change, running))
    refresh_thread.start()


    icon.menu = update_menu(icon, ip_address, last_change)  # Pass the required arguments
    icon.run()

    update_thread.join()
    refresh_thread.join()

def refresh_menu(icon, ip_address, last_change, running):
    while running[0]:
        if icon:
            time.sleep(1)  # Refresh every second or choose a suitable interval
            elapsed_time_str = get_elapsed_time(last_change)
            status = "On" if icon.icon.getpixel((0, 0)) == (0, 128, 0) else "Off"
            icon.title = f"{status} {elapsed_time_str}"  # Update tooltip text
            print(f"Elapsed Time: {elapsed_time_str}")  # Print the elapsed time
            icon.update_menu()  # Update the menu to reflect the new elapsed time






def interval_menu():
    return pystray.Menu(
        item('1 sec', lambda: update_interval(1)),
        item('10 sec', lambda: update_interval(10)),
        item('1 min', lambda: update_interval(60)),
        item('10 min', lambda: update_interval(600))
    )

def update_menu(icon, ip_address, last_change):
    elapsed_time_str = get_elapsed_time(last_change)
    status = "On" if icon.icon.getpixel((0, 0)) == (0, 128, 0) else "Off"
    icon.title = f"{status} - Elapsed time: {elapsed_time_str}"

    return pystray.Menu(
        item('Update Interval', interval_menu()),
        item(f'{ip_address[0]})', lambda: set_ip(icon, ip_address, running)),
        item('Exit', lambda: exit_program(icon, running))
    )

def get_elapsed_time(last_change):
    elapsed_time = datetime.datetime.now() - last_change[0]
    elapsed_minutes = int(elapsed_time.total_seconds() / 60)
    elapsed_seconds = int(elapsed_time.total_seconds() % 60)
    return f"{elapsed_minutes} min {elapsed_seconds} sec"

def exit_program(icon, running):
    running[0] = False  # Signal all threads to stop
    interval_changed.set()  # Trigger to break waiting in update_tray_icon
    icon.stop()  # Stop the icon


if __name__ == "__main__":
    ip_address = ['192.168.146.139']  
    running = [True]
    last_change = [datetime.datetime.now()]
    try:
        create_tray_icon(ip_address, running, last_change)
    except Exception as e:
        print(f"Error occurred: {e}")
    finally:
        running[0] = False
        if 'update_thread' in locals():
            update_thread.join()
        if 'refresh_thread' in locals():
            refresh_thread.join()
        time.sleep(1)
