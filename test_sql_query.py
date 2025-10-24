#!/usr/bin/env python
"""
Quick SQL test - runs fast
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wingz_api.settings')
django.setup()

from django.db import connection

# Quick database check
with connection.cursor() as cursor:
    print("=== QUICK DATABASE CHECK ===")
    
    # Rides
    cursor.execute("SELECT COUNT(*) FROM rides")
    rides = cursor.fetchone()[0]
    print(f"Total rides: {rides}")
    
    cursor.execute("SELECT COUNT(*) FROM rides WHERE id_driver IS NOT NULL")
    rides_with_driver = cursor.fetchone()[0]
    print(f"Rides with drivers: {rides_with_driver}")
    
    # Events
    cursor.execute("SELECT description, COUNT(*) FROM ride_events GROUP BY description")
    events = cursor.fetchall()
    print(f"\nEvents:")
    for desc, count in events:
        print(f"  '{desc}': {count}")
    
    # Drivers
    cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'driver'")
    drivers = cursor.fetchone()[0]
    print(f"\nDrivers: {drivers}")
    
    # First, let's see what trips we have and their durations
    print(f"\n=== CHECKING TRIP DURATIONS ===")
    duration_sql = """
    SELECT 
        r.id_ride,
        pickup_event.created_at as pickup_time,
        dropoff_event.created_at as dropoff_time,
        (julianday(dropoff_event.created_at) - julianday(pickup_event.created_at)) * 24 as duration_hours,
        driver.first_name || ' ' || driver.last_name as driver_name
    FROM rides r
    INNER JOIN users driver ON r.id_driver = driver.id_user
    INNER JOIN ride_events pickup_event ON r.id_ride = pickup_event.id_ride 
        AND pickup_event.description = 'Status changed to pickup'
    INNER JOIN ride_events dropoff_event ON r.id_ride = dropoff_event.id_ride 
        AND dropoff_event.description = 'Status changed to dropoff'
        AND dropoff_event.created_at > pickup_event.created_at
    ORDER BY duration_hours DESC;
    """
    
    try:
        cursor.execute(duration_sql)
        trips = cursor.fetchall()
        print(f"Found {len(trips)} complete trips:")
        for trip in trips:
            ride_id, pickup, dropoff, hours, driver = trip
            print(f"  Ride {ride_id}: {hours:.2f} hours (Driver: {driver})")
    except Exception as e:
        print(f"Duration check error: {e}")
    
    # Test the original SQL (trips > 1 hour)
    print(f"\n=== TESTING SQL QUERY (Trips > 1 hour) ===")
    sql = """
    SELECT 
        strftime('%Y-%m', pickup_event.created_at) as Month,
        (driver.first_name || ' ' || substr(driver.last_name, 1, 1)) as Driver,
        COUNT(*) as "Count of Trips > 1 hr"
    FROM rides r
    INNER JOIN users driver ON r.id_driver = driver.id_user
    INNER JOIN ride_events pickup_event ON r.id_ride = pickup_event.id_ride 
        AND pickup_event.description = 'Status changed to pickup'
    INNER JOIN ride_events dropoff_event ON r.id_ride = dropoff_event.id_ride 
        AND dropoff_event.description = 'Status changed to dropoff'
        AND dropoff_event.created_at > pickup_event.created_at
    WHERE (julianday(dropoff_event.created_at) - julianday(pickup_event.created_at)) * 24 > 1
    GROUP BY Month, Driver
    ORDER BY Month, Driver;
    """
    
    try:
        cursor.execute(sql)
        results = cursor.fetchall()
        print(f"SQL Results (>1 hour): {len(results)} rows")
        for row in results:
            print(f"  {row}")
    except Exception as e:
        print(f"SQL Error: {e}")
    
    # Test with lower threshold (trips > 0.01 hours = 36 seconds)
    print(f"\n=== TESTING SQL QUERY (Trips > 36 seconds) ===")
    sql_short = """
    SELECT 
        strftime('%Y-%m', pickup_event.created_at) as Month,
        (driver.first_name || ' ' || substr(driver.last_name, 1, 1)) as Driver,
        COUNT(*) as "Count of Trips > 36 sec"
    FROM rides r
    INNER JOIN users driver ON r.id_driver = driver.id_user
    INNER JOIN ride_events pickup_event ON r.id_ride = pickup_event.id_ride 
        AND pickup_event.description = 'Status changed to pickup'
    INNER JOIN ride_events dropoff_event ON r.id_ride = dropoff_event.id_ride 
        AND dropoff_event.description = 'Status changed to dropoff'
        AND dropoff_event.created_at > pickup_event.created_at
    WHERE (julianday(dropoff_event.created_at) - julianday(pickup_event.created_at)) * 24 > 0.01
    GROUP BY Month, Driver
    ORDER BY Month, Driver;
    """
    
    try:
        cursor.execute(sql_short)
        results = cursor.fetchall()
        print(f"SQL Results (>36 sec): {len(results)} rows")
        for row in results:
            print(f"  {row}")
    except Exception as e:
        print(f"SQL Error: {e}")

print("Done!")
