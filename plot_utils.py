"""
Common plotting module
Provides unified plotting functions for main code and debug scripts
"""
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import os
from mod_config import MODS, MAIN_MOD_ID

def plot_trends_from_csv(data_file, plot_file):
    """
    Read data from CSV file and plot trends
    
    Args:
        data_file: Path to CSV file
        plot_file: Path to output image file
    """
    try:
        if not os.path.exists(data_file):
            print(f"ERROR: No data file to plot: {data_file}")
            return False

        print(f"Reading data from {data_file}...")
        
        df = pd.read_csv(data_file)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Determine appropriate time precision based on data span
        time_span = df['timestamp'].max() - df['timestamp'].min()
        days = time_span.total_seconds() / 86400
        
        # Choose precision level based on data span
        if days < 1:
            # Less than 1 day: use minute precision
            precision = 'min'
            date_format = '%m-%d %H:%M'
        elif days < 7:
            # Less than 1 week: use hour precision
            precision = 'h'
            date_format = '%m-%d %H:00'
        elif days < 30:
            # Less than 1 month: use day precision
            precision = 'D'
            date_format = '%m-%d'
        else:
            # More than 1 month: use week precision
            precision = 'W'
            date_format = '%m-%d'
        
        print(f"Data span: {days:.2f} days, using {precision} precision")
        
        # Normalize timestamps based on selected precision
        if precision == 'min':
            df['timestamp_normalized'] = df['timestamp'].dt.floor('min')
        elif precision == 'h':
            df['timestamp_normalized'] = df['timestamp'].dt.floor('h')
        elif precision == 'D':
            df['timestamp_normalized'] = df['timestamp'].dt.floor('D')
        else:  # 'W'
            df['timestamp_normalized'] = df['timestamp'].dt.to_period('W').dt.start_time
        
        # Align all mods to main mod timestamps
        if MAIN_MOD_ID is not None and MAIN_MOD_ID in df['mod_id'].values:
            # Get main mod timestamps
            main_mod_timestamps = df[df['mod_id'] == MAIN_MOD_ID]['timestamp_normalized'].unique()
            main_mod_timestamps = sorted(main_mod_timestamps)
            
            if len(main_mod_timestamps) > 0:
                # For each data point, find the nearest main mod timestamp
                def align_to_main(timestamp):
                    # Find the nearest main mod timestamp
                    idx = np.searchsorted(main_mod_timestamps, timestamp, side='left')
                    if idx == 0:
                        return main_mod_timestamps[0]
                    elif idx == len(main_mod_timestamps):
                        return main_mod_timestamps[-1]
                    else:
                        # Choose the closer one
                        left = main_mod_timestamps[idx - 1]
                        right = main_mod_timestamps[idx]
                        if abs((timestamp - left).total_seconds()) < abs((timestamp - right).total_seconds()):
                            return left
                        else:
                            return right
                
                # Apply alignment
                df['timestamp_aligned'] = df['timestamp_normalized'].apply(align_to_main)
                df['timestamp'] = df['timestamp_aligned']  # Use aligned timestamp for plotting
            else:
                df['timestamp'] = df['timestamp_normalized']
        else:
            # If no main mod found, just use normalized timestamps
            df['timestamp'] = df['timestamp_normalized']
        
        # Sort by time
        df = df.sort_values('timestamp')
        
        # Remove duplicates: for each (timestamp, mod_id) combination, keep only the latest one
        # This prevents double-counting when multiple data points align to the same timestamp
        df = df.drop_duplicates(subset=['timestamp', 'mod_id'], keep='last')
        
        # Use xkcd style, but need special handling to avoid dash pattern errors
        try:
            # Try using xkcd style
            with plt.xkcd():
                fig = plt.figure(figsize=(12, 8))
                ax = fig.add_subplot(111)
                
                mod_ids = df['mod_id'].unique()
                # Calculate totals using aligned timestamps (after deduplication)
                total_subs = df.groupby('timestamp')['subscribers'].sum().reset_index()
                
                print(f"Found {len(mod_ids)} mods and {len(df)} data points.")
                
                # Plot each mod's curve
                for mod_id in mod_ids:
                    mod_data = df[df['mod_id'] == mod_id].sort_values('timestamp')
                    if mod_data.empty: continue
                    
                    # Get name from config
                    mod_name = MODS.get(mod_id, {}).get('name', f'Mod {mod_id}')
                    
                    # Plot line and points
                    ax.plot(mod_data['timestamp'], mod_data['subscribers'], label=mod_name, marker='o', markersize=4, linewidth=2)
                    
                    # Display value at the last point
                    last_point = mod_data.iloc[-1]
                    ax.text(last_point['timestamp'], last_point['subscribers'], 
                             f" {int(last_point['subscribers'])}", 
                             fontsize=9, ha='left', va='center')

                # Plot total curve - use solid line to avoid dash issues
                if not total_subs.empty:
                    ax.plot(total_subs['timestamp'], total_subs['subscribers'], label='Total', 
                            linestyle='-', linewidth=2.5, color='black', marker='x', alpha=0.7)
                    
                    last_total = total_subs.iloc[-1]
                    ax.text(last_total['timestamp'], last_total['subscribers'], 
                             f" Total: {int(last_total['subscribers'])}", 
                             fontsize=10, fontweight='bold', ha='left', va='center')

                ax.set_title('Steam Mod Subscription Trends', fontsize=16)
                ax.set_xlabel('Time', fontsize=12)
                ax.set_ylabel('Subscribers', fontsize=12)
                
                # Use appropriate date format based on precision
                ax.xaxis.set_major_formatter(mdates.DateFormatter(date_format))
                fig.autofmt_xdate() # Auto-rotate date labels
                
                # Grid lines - use simpler style
                ax.grid(True, linestyle='-', alpha=0.2, linewidth=0.5)
                ax.legend(loc='best')
                fig.tight_layout()
                
                plt.savefig(plot_file)
                plt.close()
                # Verify file was created
                if not os.path.exists(plot_file):
                    print(f"ERROR: Plot file was not created: {plot_file}")
                    return False
                print(f"Plot saved to {plot_file}")
                return True
        except Exception as xkcd_error:
            # If xkcd style fails, use normal style
            print(f"XKCD style failed: {xkcd_error}, using normal style...")
            fig = plt.figure(figsize=(12, 8))
            ax = fig.add_subplot(111)
            
            mod_ids = df['mod_id'].unique()
            # Calculate totals using aligned timestamps (after deduplication)
            total_subs = df.groupby('timestamp')['subscribers'].sum().reset_index()
            
            print(f"Found {len(mod_ids)} mods and {len(df)} data points.")
            
            # Plot each mod's curve
            for mod_id in mod_ids:
                mod_data = df[df['mod_id'] == mod_id].sort_values('timestamp')
                if mod_data.empty: continue
                
                mod_name = MODS.get(mod_id, {}).get('name', f'Mod {mod_id}')
                ax.plot(mod_data['timestamp'], mod_data['subscribers'], label=mod_name, marker='o', markersize=4, linewidth=2)
                
                last_point = mod_data.iloc[-1]
                ax.text(last_point['timestamp'], last_point['subscribers'], 
                         f" {int(last_point['subscribers'])}", 
                         fontsize=9, ha='left', va='center')

            if not total_subs.empty:
                ax.plot(total_subs['timestamp'], total_subs['subscribers'], label='Total', 
                        linestyle='--', linewidth=2, color='black', marker='x')
                
                last_total = total_subs.iloc[-1]
                ax.text(last_total['timestamp'], last_total['subscribers'], 
                         f" Total: {int(last_total['subscribers'])}", 
                         fontsize=10, fontweight='bold', ha='left', va='center')

            ax.set_title('Steam Mod Subscription Trends', fontsize=16)
            ax.set_xlabel('Time', fontsize=12)
            ax.set_ylabel('Subscribers', fontsize=12)
            
            # Use appropriate date format based on precision
            ax.xaxis.set_major_formatter(mdates.DateFormatter(date_format))
            fig.autofmt_xdate()
            
            ax.grid(True, linestyle='--', alpha=0.5)
            ax.legend(loc='best')
            fig.tight_layout()
            
            plt.savefig(plot_file)
            plt.close()
            # Verify file was created
            if not os.path.exists(plot_file):
                print(f"ERROR: Plot file was not created: {plot_file}")
                return False
            print(f"Plot saved to {plot_file}")
            return True

    except Exception as e:
        print(f"ERROR: Plotting failed: {e}")
        import traceback
        traceback.print_exc()
        return False

