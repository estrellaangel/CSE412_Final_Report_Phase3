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
