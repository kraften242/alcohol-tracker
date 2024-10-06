import curses
import csv
from datetime import datetime, timedelta
import os

FILENAME = 'alcohol_log.csv'

# Initialize log file if it doesn't exist
if not os.path.exists(FILENAME):
    with open(FILENAME, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['Date', 'Drink', 'Volume (cl)', 'Cost (SEK)'])

# Function to add a drink entry (including multiple)
def add_drink(screen, for_date=None):
    screen.clear()
    curses.echo()
    
    screen.addstr(0, 0, "Enter drink name: ")
    drink = screen.getstr(0, 20, 20).decode('utf-8')
    
    screen.addstr(1, 0, "Enter volume in cl: ")
    volume = float(screen.getstr(1, 20, 20).decode('utf-8'))
    
    screen.addstr(2, 0, "Enter cost in SEK: ")
    cost = float(screen.getstr(2, 20, 20).decode('utf-8'))

    screen.addstr(3, 0, "How many? ")
    count = int(screen.getstr(3, 20, 2).decode('utf-8'))

    # Use given date or current date
    if for_date:
        date_str = for_date
    else:
        date_str = datetime.now().strftime('%Y-%m-%d')
    
    with open(FILENAME, 'a', newline='') as file:
        writer = csv.writer(file)
        for _ in range(count):
            writer.writerow([date_str, drink, volume, cost])
    
    screen.addstr(5, 0, f"{count} drinks added successfully!")
    screen.addstr(6, 0, "Press any key to return to menu.")
    screen.getch()

# Function to get statistics
def get_stats(timeframe, specific_date=None):
    total_volume = 0
    total_cost = 0
    latest_drink = None
    cutoff_date = datetime.now() - timeframe if not specific_date else specific_date
    
    with open(FILENAME, 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            date = datetime.strptime(row['Date'], '%Y-%m-%d')
            if (specific_date and date == specific_date) or (not specific_date and date >= cutoff_date):
                total_volume += float(row['Volume (cl)'])
                total_cost += float(row['Cost (SEK)'])
            latest_drink = row
    
    return total_volume, total_cost, latest_drink

# Function to get total cost for the current month
def get_monthly_cost():
    total_cost = 0
    current_month = datetime.now().month
    current_year = datetime.now().year

    with open(FILENAME, 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            date = datetime.strptime(row['Date'], '%Y-%m-%d')
            if date.month == current_month and date.year == current_year:
                total_cost += float(row['Cost (SEK)'])

    return total_cost

# Display statistics on the screen
def display_stats(screen, timeframe, title):
    total_volume, total_cost, _ = get_stats(timeframe)
    
    screen.clear()
    screen.addstr(0, 0, f"{title} Stats:")
    screen.addstr(1, 0, f"Total Volume Consumed (cl): {total_volume}")
    screen.addstr(2, 0, f"Total Cost (SEK): {total_cost}")
    screen.addstr(4, 0, "Press any key to return to menu.")
    screen.getch()

# Add a drink for another day (including multiple drinks)
def add_drink_for_another_day(screen):
    screen.clear()
    curses.echo()
    
    screen.addstr(0, 0, "Enter the date (YYYY-MM-DD): ")
    date_str = screen.getstr(0, 30, 20).decode('utf-8')
    
    # Validate date input
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
        add_drink(screen, date_str)
    except ValueError:
        screen.addstr(2, 0, "Invalid date format. Press any key to return to menu.")
        screen.getch()

# Function to list and remove drinks
def remove_drink(screen):
    screen.clear()

    # Read all drinks from the file
    drinks = []
    with open(FILENAME, 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            drinks.append(row)

    if not drinks:
        screen.addstr(2, 0, "No drinks found. Press any key to return to menu.")
        screen.getch()
        return

    # Show the latest 10 drinks (or fewer if there are less than 10)
    drinks_to_display = drinks[-10:]

    screen.addstr(0, 0, "Latest 10 Drinks:")
    for idx, drink in enumerate(reversed(drinks_to_display)):
        screen.addstr(idx + 1, 0, f"{idx+1} - {drink['Date']}: {drink['Drink']} ({drink['Volume (cl)']} cl, {drink['Cost (SEK)']} SEK)")

    screen.addstr(len(drinks_to_display) + 2, 0, "Enter the number of the drink to remove: ")
    try:
        choice = int(screen.getstr(len(drinks_to_display) + 2, 40, 2).decode('utf-8')) - 1
        if choice < 0 or choice >= len(drinks_to_display):
            raise ValueError
    except ValueError:
        screen.addstr(len(drinks_to_display) + 3, 0, "Invalid choice. Press any key to return to menu.")
        screen.getch()
        return

    # Remove selected drink from the file
    remaining_entries = []
    selected_drink = drinks_to_display[::-1][choice]
    with open(FILENAME, 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            if row != selected_drink:
                remaining_entries.append(row)

    # Write back the remaining entries to the CSV file
    with open(FILENAME, 'w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=['Date', 'Drink', 'Volume (cl)', 'Cost (SEK)'])
        writer.writeheader()
        writer.writerows(remaining_entries)

    screen.addstr(len(drinks_to_display) + 5, 0, "Drink removed successfully. Press any key to return to menu.")
    screen.getch()

# Main menu
def main_menu(screen):
    while True:
        screen.clear()
        
        # Get daily stats and the latest drink added
        daily_volume, daily_cost, latest_drink = get_stats(timedelta(days=1), datetime.now())
        monthly_cost = get_monthly_cost()
        
        # Display the menu
        screen.addstr(0, 0, "Alcohol Tracker")
        screen.addstr(1, 0, f"Today's Total Volume (cl): {daily_volume}")
        screen.addstr(2, 0, f"Today's Total Cost (SEK): {daily_cost}")
        screen.addstr(3, 0, f"Cost so far this month (SEK): {monthly_cost}")
        screen.addstr(4, 0, f"Latest Drink: {latest_drink['Drink']} ({latest_drink['Volume (cl)']} cl, {latest_drink['Cost (SEK)']} SEK)" if latest_drink else "Latest Drink: None")
        screen.addstr(6, 0, "1 - Add Drink for Today")
        screen.addstr(7, 0, "2 - Add Drink for Another Day")
        screen.addstr(8, 0, "3 - View Daily Stats")
        screen.addstr(9, 0, "4 - View Weekly Stats")
        screen.addstr(10, 0, "5 - View Monthly Stats")
        screen.addstr(11, 0, "6 - Remove Drink")
        screen.addstr(12, 0, "7 - Exit")
        screen.addstr(14, 0, "Select an option: ")
        
        choice = screen.getch()
        
        if choice == ord('1'):
            add_drink(screen)
        elif choice == ord('2'):
            add_drink_for_another_day(screen)
        elif choice == ord('3'):
            display_stats(screen, timedelta(days=1), "Daily")
        elif choice == ord('4'):
            display_stats(screen, timedelta(weeks=1), "Weekly")
        elif choice == ord('5'):
            display_stats(screen, timedelta(days=30), "Monthly")
        elif choice == ord('6'):
            remove_drink(screen)
        elif choice == ord('7'):
            break

# Main function
def main():
    curses.wrapper(main_menu)

if __name__ == "__main__":
    main()
