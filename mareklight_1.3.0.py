import threading
from PIL import Image
import pystray
from pystray import MenuItem as item
import subprocess
import tkinter as tk
from tkinter import simpledialog
import time
import datetime
import requests
import re
import os  # Add this line
import sys  # Add this line
from scapy.all import ARP, Ether, srp

# Create and hide the root window immediately
root = tk.Tk()
root.withdraw()

PING_INTERVAL = 60  # Time between pings in seconds
update_lock = threading.Lock() 
interval_changed = threading.Event()  # Add this line


def get_executable_path():
    return os.path.dirname(sys.executable)

def get_latest_version(repo, current_version):
    url = f"https://api.github.com/repos/Sportinger/mareklight/contents/releases/latest"
    response = requests.get(url)
    if response.status_code == 200:
        files = response.json()
        if not isinstance(files, list):
            return None
        # Assuming there is only one file in this directory
        if len(files) > 0:
            return files[0]['name'], files[0]['download_url']
    return None, None

def download_file(url, filename):
    response = requests.get(url)
    if response.status_code == 200:
        with open(filename, 'wb') as file:
            file.write(response.content)
        print(f"Downloaded {filename}")
    else:
        print("Failed to download the file.")

def parse_version(filename):
    version_regex = re.compile(r"mareklight_(\d+\.\d+\.\d+)\.exe")
    match = version_regex.search(filename)
    return match.group(1) if match else None

# Usage
repo = "Sportinger/mareklight"

def get_latest_file_info(repo):
    url = f"https://api.github.com/repos/{repo}/contents/releases/latest"
    response = requests.get(url)
    if response.status_code == 200:
        files = response.json()
        # Check if the response is a list (it should be for a directory)
        if not isinstance(files, list):
            return None
        # Assuming there is only one file in this directory
        if len(files) > 0:
            file_info = files[0]
            file_name = file_info['name']
            download_url = file_info['download_url']
            return file_name, download_url
    return None, None


current_version = '1.3.0'  # Your current app version

filename, download_url = get_latest_file_info(repo)
if filename:
    latest_version = parse_version(filename)
    if latest_version and latest_version > current_version:
        print(f"New version available: {latest_version}")
        exe_path = get_executable_path()  # Get the path of the current executable
        new_file_path = os.path.join(exe_path, filename)
        download_file(download_url, new_file_path)
        write_update_batch(exe_path, sys.executable, new_file_path)
    else:
        print("Running the latest version.")
else:
    print("No files found in the latest directory.")

def ping_ip(ip_address):
    try:
        arp = ARP(pdst=ip_address[0])
        ether = Ether(dst="ff:ff:ff:ff:ff:ff")
        packet = ether/arp

        result = srp(packet, timeout=2, verbose=0)[0]

        # If the host is up, it should respond to the ARP request
        # and the result should not be empty
        if result:
            return True, "Host is up"
        else:
            return False, "No response"
    except Exception as e:
        return False, str(e)

def create_image(color):
    # Create an image with given background color
    width = 64
    height = 64
    image = Image.new('RGB', (width, height), color)
    return image

def write_update_batch(exe_path, old_exe, new_exe):
    batch_script = os.path.join(exe_path, "update.bat")
    with open(batch_script, 'w') as bat:
        bat.write(f'@echo off\n')
        bat.write(f'timeout /t 5 /nobreak\n')
        bat.write(f'del "{old_exe}"\n')
        bat.write(f'rename "{new_exe}" "{os.path.basename(old_exe)}"\n')
        bat.write(f'start "" "{os.path.basename(old_exe)}"\n')
        bat.write(f'del "%~f0"&exit\n')
    subprocess.Popen(batch_script, shell=True)

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
        item(lambda text: ip_address[0], lambda: set_ip(icon, ip_address, running)),  # Use a function to get the current IP address
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
    ip_address = ['192.168.146.56']  
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
