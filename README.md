# Weather

This is work in progress for speculative design project about climate. It uses
[NCEI Data Access for Land-Based
Data](https://www.ncdc.noaa.gov/data-access/land-based-station-data/land-based-datasets)
to produce a realistic looking weather forecast based on historical weather data.

```console
$ python cli.py weather

                    Sunday, May 5, 2069                     

               -CURRENT WEATHER AS OF 2:53PM-               

              clear sky, rain. Wind 10mph SSW.              

        Current Temp: 93     
                High: 94             Rel. Humidity: 25     
                 Low: 49              Carbon Count: 410    

                   -YOUR HOURLY FORECAST-                   

  94   93   90   80   72   70   68   67   69   66   61   67 
 4PM  5PM  6PM  7PM  8PM  9PM 10PM 11PM 12AM  1AM  2AM  3AM 

  67   66   65   67   70   74   77   84   87   89   91   92 
 4AM  5AM  6AM  7AM  8AM  9AM 10AM 11AM 12PM  1PM  2PM  3PM 

                   -YOUR DAILY FORECAST-                    

       low temperature:    61    72    68    63    73    73
      mean temperature:    75    81    71    73    78    80
      high temperature:    92    94    78    80    87    91
                          Mon   Tue   Wed   Thu   Fri   Sat
```
