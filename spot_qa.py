import os
from logos_module import *
import easygui as eg
import pypyodbc
import test.test_version


def main():

    test.test_version.check_version()

    database_dir = ('\\\\krypton\\rtp-share$\\protons\\Work in Progress'
                    '\\Christian\\Database\\Proton\\Test FE - CB.accdb')

    conn = pypyodbc.connect(
            r'Driver={Microsoft Access Driver (*.mdb, *.accdb)};'
            r'DBQ=' + database_dir + ';'
            )
    cursor = conn.cursor()

    # Produce list of energies for multchoicebox (taken from the Database)
    cursor.execute('select * from [ProtonEnergies]')
    energy_options = [row[0] for row in cursor.fetchall()]

    # Select acquired energies
    energies = eg.multchoicebox('Select Energies',
                                'Please select the energies that '
                                'have spot pattern image files', energy_options
                                )
    if not energies:
        eg.msgbox('Please re-run the code and select the acquired energies',
                  title='Energy selection box closed by user')
        raise SystemExit

    energies = sorted([float(i) for i in energies], reverse=True)
    print(f'Energies acquired: {energies}\n')

    # Select Operator from list in Database
    cursor.execute('select * from [Operators]')
    operators = [row[2] for row in cursor.fetchall()]
    operator = eg.choicebox('Who performed the measurements?',
                            'Operator',
                            operators)
    if not operator:
        eg.msgbox('Please re-run the code and select an Operator')
        raise SystemExit
    print(f'Operator = {operator}\n')

    # Select Gantry from list in Database
    cursor.execute('select * from [MachinesQuery]')
    machines = [row[0] for row in cursor.fetchall()]
    gantry = eg.choicebox('Which room were the measurements performed in?',
                          'Gantry',
                          machines)
    if not gantry:
        eg.msgbox('Please re-run the code and select a room')
        raise SystemExit
    print(f'Gantry = {gantry}\n')

    # Select Gantry Angle
    gantry_angles = [0, 90, 180, 270, 'Other']
    gantry_angle = eg.choicebox('What gantry angle were the measurements taken'
                                ' at?', 'Ganty Angle', gantry_angles)
    if gantry_angle == 'Other':
        gantry_angle = eg.integerbox(msg='Please enter gantry angle (Integer '
                                     'between 0-360)', title='Gantry Angle',
                                     lowerbound=0, upperbound=360)
    if not gantry_angle:
        eg.msgbox('Please re-run the code and select the gantry angle used')
        raise SystemExit
    print(f'Gantry Angle = {gantry_angle}\n')

    # Select equipment - Eventually this should be linked to an appropriate
    # database querry not hardcoded.
    equipment_list = ['XRV-3000 Eagle 2D Beam Profiler [1]',
                      'XRV-4000 2D Beam Profiler [1]']
    equipment = eg.choicebox('Which equipment was used?', 'Equipment',
                             equipment_list)
    if not equipment:
        eg.msgbox('Please re-run the code and select the equipment used')
        raise SystemExit
    print(f'Equipment = {equipment}\n')

    # User selects directory containing all acquired spot grid energies
    dir = eg.diropenbox('Select Folders Containing Acquired Images '
                        'For All Acquired Energies')

    if not dir:
        eg.msgbox('Please re-run the code and select a folder containing the '
                  'data to be analysed', title='Folder Selection Error')
        raise SystemExit

    # Check to ensure number of energies defined matches the number of images
    if not len(energies) == len(os.listdir(dir)):
        eg.msgbox('Number of files in directory does not match number of '
                  'Energies selected\nPlease re-run the program',
                  'File Count Error')
        raise SystemExit

    # Loop to check that output and active script files are present
    for foldername in sorted(os.listdir(dir)):
        path = os.path.join(dir, foldername)

        if not os.path.isfile(os.path.join(path, 'activescript.txt')):
            eg.msgbox(f"Folder {foldername} Doesn't contain the activescript "
                      "file required to calculate the image resolution")
            raise SystemExit

        if not os.path.isfile(os.path.join(path, 'output.txt')):
            eg.msgbox(f"Folder {foldername} Doesn't contain the output file "
                      "required for the spot data")
            raise SystemExit

        if not os.path.isfile(os.path.join(path, '00000001.bmp')):
            eg.msgbox(f"Folder {foldername} Doesn't contain an image "
                      "Code will terminate")
            raise SystemExit

    # Create list of paths to output files
    output_files = [os.path.join(os.path.join(dir, dirnames), 'output.txt')
                    for dirnames in os.listdir(dir)]

    # Generate output dictionary from output_file_path with energy as the key
    spot_properties = {x: Output(output_files[energies.index(x)])
                       for x in energies}

    image_locs = [os.path.join(os.path.join(dir, dirnames), '00000001.bmp')
                  for dirnames in os.listdir(dir)]

    ###########################################################################
    # Print Results and input to DB
    ###########################################################################

    sql = ('INSERT INTO [Spot Profile] ([ADate], [Operator], [Equipment], '
           '[MachineName], [GantryAngle], [Energy], [Spot Position], '
           '[X-Position], [Y-Position], [Spot Size (Ave FWHM)], '
           '[Eccentricity], [Image File Location]) \n'
           'VALUES(?,?,?,?,?,?,?,?,?,?,?,?)'
           )
    spot_pos = ['top-left', 'top-centre', 'top-right',
                'middle-left', 'middle-centre', 'middle-right',
                'bottom-left', 'bottom-centre', 'bottom-right'
                ]

    for x in energies:
        print(f"Results for {x}MeV Spots:\n")
        print('Center:')
        print(spot_properties[x].center)
        print('Spot Positions:')
        print(spot_properties[x].spots_xy)
        print('Spot Width:')
        print(spot_properties[x].spots_width)
        print('Spot Height:')
        print(spot_properties[x].spots_height)
        print('Averaged Spot Diameter:')
        print(spot_properties[x].spots_diameter)
        print('Spot Circularity:')
        print(spot_properties[x].spots_quality)
        print()

        for y in range(1, (spot_properties[x].no_of_spots + 1)):
            subset = [spot_properties[x].datetime,
                      operator,
                      equipment,
                      gantry,
                      gantry_angle,
                      x,
                      spot_pos[y-1],
                      spot_properties[x].spots_xy[y][0],
                      spot_properties[x].spots_xy[y][1],
                      spot_properties[x].spots_diameter[y],
                      spot_properties[x].spots_quality[y],
                      image_locs[energies.index(x)]
                      ]

            try:
                cursor.execute(sql, subset)
            except pypyodbc.IntegrityError:
                eg.msgbox(f'Data for energy {x} already exists in database\n'
                          'Please come up with something original',
                          title='Data duplication')
                raise SystemExit

    # Commit the changes to the database
    conn.commit()


if __name__ == '__main__':
    main()
