# database.py
import psycopg2
import pandas as pd
import io
from tkinter import messagebox


class DatabaseManager:
    #Backend of the progam that serves as the middle man between the db and the front end
    def __init__(self):
        #main constructer will start the connection in the next method
        self.conn = None
        self.init_connection()
    
    def init_connection(self):
        """Init database connection"""
        try:
            self.conn = psycopg2.connect(
                dbname="postgres",
                user="postgres",
                password="newpassword",
                host="localhost",
                port="5432"
            )
            #debug messages
            print("Database connection successful")
        except Exception as e:
            print(f"Database connection failed: {e}")
            self.conn = None
    
    def get_states(self):
        """get unique states from the db"""
        try:
            with self.conn.cursor() as cur:
                cur.execute("SELECT DISTINCT stateabbr FROM housing_data ORDER BY stateabbr;")
                return [state[0] for state in cur.fetchall()]
        except Exception as e:
            print(f"error fetching states: {e}")
            return []

    def suggest_cities(self, partial_name, state=None):
        """get city suggestions based on entry input"""
        try:
            with self.conn.cursor() as cur:
                if state:
                    #command  to search for city that has certain  state
                    cur.execute(
                        """
                        SELECT DISTINCT city 
                        FROM housing_data 
                        WHERE city ILIKE %s AND stateabbr = %s 
                        ORDER BY city 
                        LIMIT 10;
                        """,
                        (f"{partial_name}%", state)
                    )
                else:
                    #no state
                    cur.execute(
                        """
                        SELECT DISTINCT city 
                        FROM housing_data 
                        WHERE city ILIKE %s 
                        ORDER BY city 
                        LIMIT 10;
                        """,
                        (f"{partial_name}%",)
                    )
                return [city[0] for city in cur.fetchall()] #return a list
        except Exception as e:
            print(f"Error suggesting cities: {e}")
            return []

    def suggest_zipcodes(self, partial_zipcode, state=None, city=None):
        """same as suggest cities but gets zipcodes based of state or city input"""
        try:
            with self.conn.cursor() as cur:
                conditions = ["zipcode::text LIKE %s"]
                params = [f"{partial_zipcode}%"]
                
                if state:
                    conditions.append("stateabbr = %s")
                    params.append(state)
                if city:
                    conditions.append("city = %s")
                    params.append(city)
                
                query = f"""
                    SELECT DISTINCT zipcode 
                    FROM housing_data 
                    WHERE {' AND '.join(conditions)}
                    ORDER BY zipcode 
                    LIMIT 10;
                """
                cur.execute(query, tuple(params))
                return [str(zipcode[0]) for zipcode in cur.fetchall()] # return list of zipcodes
        except Exception as e:
            print(f"Error suggesting zipcodes: {e}")
            return []
    
    def fetch_housing_data(self, state=None, city=None, zipcode=None, start_date=None, end_date=None):
        """Main function to grab actual data points to be used by visualization.py to plot"""
        if not self.conn:
            print("No database connection")
            return None

        try:#handle erros graecfully
            conditions = []
            params = []
            group_by_cols = ['date']  # group by date
            select_cols = ['date']

            # get the filters and add the condition if state city or zip included
            if state:
                conditions.append("stateabbr = %s")
                params.append(state)
                select_cols.append("stateabbr")
                group_by_cols.append("stateabbr")

                if city:
                    conditions.append("city = %s")
                    params.append(city)
                    select_cols.append("city")
                    group_by_cols.append("city")

                    if zipcode:
                        conditions.append("zipcode = %s::integer")
                        params.append(zipcode)
                        select_cols.append("zipcode")
                        group_by_cols.append("zipcode")
            #get the date start and end
            if start_date:
                conditions.append("date >= %s::date")
                params.append(start_date)
            if end_date:
                conditions.append("date <= %s::date")
                params.append(end_date)

            where_clause = " AND ".join(conditions) if conditions else "1=1" #end in true to handle errors

            # grab data that has Zhvi available and then get the average and order by date
            query = f"""
                WITH filtered_data AS (
                    SELECT *
                    FROM housing_data 
                    WHERE {where_clause}
                    AND zhvi IS NOT NULL
                )
                SELECT {', '.join(select_cols)}, 
                       AVG(zhvi) as price,
                       COUNT(DISTINCT zipcode) as included_zipcodes
                FROM filtered_data
                GROUP BY {', '.join(group_by_cols)}
                ORDER BY date;
            """
            #send query
            with self.conn.cursor() as cur:
                cur.execute(query, tuple(params))
                results = cur.fetchall()

            # get column anmes
            columns = select_cols + ['price', 'included_zipcodes']
            df = pd.DataFrame(results, columns=columns)

            if df.empty:
                print("No data found for the given criteria")
            else:
                # debug prints in the console
                location_desc = "state" if state and not city else "city" if city else "overall"
                avg_zipcodes = df['included_zipcodes'].mean()
                print(f"found {len(df)} time points for {location_desc}")
                print(f"avg across approximately {avg_zipcodes:.0f} zipcodes per time point")
            return df

        except Exception as e:
            print(f"Error getting data: {e}")
            return None
    
    def save_visualization(self, name, figure):
        """this save the plot to the the visualization db"""
        try:
            # Check if name exist
            with self.conn.cursor() as cur:
                cur.execute("""
                    SELECT visualization_id 
                    FROM visualizations 
                    WHERE visualization_name = %s;
                """, (name,))
                existing = cur.fetchone()

                if existing:
                    # if exists ask  want to update
                    if messagebox.askyesno("Name Exists", 
                        f"A visualization named '{name}' already exists. Do you want to update it?"):
                        # convert matplotlib figure to  bytes
                        img_buffer = io.BytesIO()
                        figure.savefig(img_buffer, format='png')
                        img_bytes = img_buffer.getvalue()

                        # update existing visualization
                        cur.execute("""
                            UPDATE visualizations 
                            SET visualization_data = %s 
                            WHERE visualization_name = %s
                            RETURNING visualization_id;
                        """, (img_bytes, name))
                        viz_id = cur.fetchone()[0]
                        self.conn.commit()
                        return viz_id
                    return None
                else:
                    # if doesn't exist create 
                    # convert matplotlib figure to  bytes
                    img_buffer = io.BytesIO()
                    figure.savefig(img_buffer, format='png')
                    img_bytes = img_buffer.getvalue()

                    cur.execute("""
                        INSERT INTO visualizations 
                        (visualization_name, visualization_data) 
                        VALUES (%s, %s)
                        RETURNING visualization_id;
                    """, (name, img_bytes))#store bytes
                    viz_id = cur.fetchone()[0]
                    self.conn.commit()
                    return viz_id
                
        except Exception as e:
            print(f"Error saving visualization: {e}")
            # rollback db on error
            if self.conn:
                self.conn.rollback()
            return None

    def update_visualization_name(self, old_name, new_name):
        """upadte name"""
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    UPDATE visualizations 
                    SET visualization_name = %s 
                    WHERE visualization_name = %s 
                    RETURNING visualization_id;
                """, (new_name, old_name))# use old and new name variables
                updated_id = cur.fetchone()
                self.conn.commit()
                return updated_id[0] if updated_id else None
        except Exception as e:
            print(f"Error updating visualization name: {e}")
            return None

    def delete_visualization(self, name):
        """delete visualization useing name"""
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    DELETE FROM visualizations 
                    WHERE visualization_name = %s
                    RETURNING visualization_id;
                """, (name,))#use the name of the visual
                deleted_id = cur.fetchone()
                self.conn.commit()
                return deleted_id[0] if deleted_id else None
        except Exception as e:
            print(f"Error deleting visualization: {e}")
            return None

    def get_visualization_list(self):
        """get list of visuals"""
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    SELECT visualization_name 
                    FROM visualizations 
                    ORDER BY visualization_id;
                """)
                return cur.fetchall()
        except Exception as e:
            print(f"Error fetching visualizations: {e}")
            return []

    def get_visualization(self, name):
        """get the plot image"""
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    SELECT visualization_data 
                    FROM visualizations 
                    WHERE visualization_name = %s;
                """, (name,))
                result = cur.fetchone()
                return result[0] if result else None
        except Exception as e:
            print(f"Error fetching visualization: {e}")
            return None
