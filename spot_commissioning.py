import os
from urllib.request import urlopen, URLError
import easygui as eg
import xlsxwriter
import test.test_version
import logos_module as lm
import numpy as np

def main():
    dir = eg.diropenbox(title='Please select location of tiff files\n')

    if not dir:
        print('No directory selected:')
        print('Code terminated')
        input('Press enter to close window')
        raise SystemExit

    file_list = os.listdir(dir)

    if 'activescript.txt' and 'output.txt' not in file_list:
        print('activescript.txt or output.tx file not found')
        print('These are both required to analyse images')
        print('Code Terminated')
        input('Press enter to close window')
        raise SystemExit
    else:
        print('activescript.txt and output.txt files found\n')

    image_list = [f for f in os.listdir(dir) if f.endswith(('.tif', '.tiff',
                                                            '.jpg', '.bmp'))]
    # Sort by filename which should equate to beam energy
    image_list = sorted(image_list, key=lambda f: int(os.path.splitext(f)[0]))

    # activescript object contains resolution info output from Beamworks
    active_script = lm.ActiveScript(os.path.join(dir,'activescript.txt'))
    resolution = [active_script.CameraHRatio, active_script.CameraVRatio]

    savename = eg.filesavebox('Save as', 'Results')

    workbook = xlsxwriter.Workbook(savename +'.xlsx')

    for key in image_list:

        array = lm.image_to_array(os.path.join(dir,key)) # A numpy array
        center = lm.find_centre(array) # A List, [CenterRow, CenterCol]
        x_prof, y_prof = lm.central_xy_profiles(array, center, resolution)

        x_half = int(x_prof.shape[1]/2)
        x_half_plus_ten = 10+int(x_prof.shape[1]/2)
        y_half = int(y_prof.shape[1]/2)
        y_half_plus_ten = 10+int(y_prof.shape[1]/2)

        x_prof_log = np.asarray([x_prof[0],np.log10(x_prof[1])])
        y_prof_log = np.asarray([y_prof[0],np.log10(y_prof[1])])

        x_prof_log_l = x_prof_log[:,0:x_half_plus_ten]
        x_prof_log_r = x_prof_log[:,-x_half_plus_ten::]
        y_prof_log_l = y_prof_log[:,0:y_half_plus_ten]
        y_prof_log_r = y_prof_log[:,-y_half_plus_ten::]


        x_params_l = lm.log_2_gaus_shift_fit(x_prof_log_l)
        x_params_r = lm.log_2_gaus_shift_fit(x_prof_log_r)
        y_params_l = lm.log_2_gaus_shift_fit(y_prof_log_l)
        y_params_r = lm.log_2_gaus_shift_fit(y_prof_log_r)

        x_fit_l = 10**lm.log_2_gaus_shift_func(x_prof_log_l[0],*x_params_l)
        x_fit_r = 10**lm.log_2_gaus_shift_func(x_prof_log_r[0],*x_params_r)
        y_fit_l = 10**lm.log_2_gaus_shift_func(y_prof_log_l[0],*y_params_l)
        y_fit_r = 10**lm.log_2_gaus_shift_func(y_prof_log_r[0],*y_params_r)

        x_model = [x_prof[0], np.concatenate([x_fit_l[0:x_half],x_fit_r[-x_half:]])]
        y_model = [y_prof[0], np.concatenate([y_fit_l[0:y_half],y_fit_r[-y_half:]])]

        # plt.plot(x_prof_log_l[0],10**x_prof_log_l[1])
        # plt.plot(x_prof_log_l[0],10**x_fit_l)
        # plt.plot(x_prof_log_r[0],10**x_prof_log_r[1])
        # plt.plot(x_prof_log_r[0],10**x_fit_r)
        # plt.show()
        energy = key.split('.')[0]
        worksheet=workbook.add_worksheet(energy)
        worksheet.write('B2', 'X Distance mm')
        worksheet.write_column('B3',x_prof[0])
        worksheet.write('C2', 'X Data')
        worksheet.write_column('C3',x_prof[1])
        worksheet.write('D2', 'X Model')
        worksheet.write_column('D3', x_model[1])
        worksheet.write('E2', 'Y Distance mm')
        worksheet.write_column('E3',y_prof[0])
        worksheet.write('F2', 'Y Data')
        worksheet.write_column('F3',y_prof[1])
        worksheet.write('G2', 'Y Model')
        worksheet.write_column('G3', y_model[1])

        worksheet.set_column(1,6,14)

        chart1 = workbook.add_chart({'type': 'scatter'})
        chart1.add_series({
            'name':       'Data',
            'categories': "".join("="+energy+"!$B$3:$B$"+str(2+len(x_prof[0]))),
            'values':     "".join("="+energy+"!$C$3:$C$"+str(2+len(x_prof[1]))),
            'line': {'color':'red', 'width': 1,},
            'marker': {'type':'none'},
        })
        chart1.add_series({
            'name':       'Model',
            'categories': "".join("="+energy+"!$B$3:$B$"+str(2+len(x_prof[0]))),
            'values':     "".join("="+energy+"!$D$3:$D$"+str(2+len(x_model[1]))),
            'line': {'color':'blue', 'width': 1,},
            'marker': {'type':'none'},
        })
        chart1.set_title ({'name': 'X Profile'})
        chart1.set_x_axis({'name': 'X_Coordinate (mm)'})
        chart1.set_y_axis({'name': 'Relative intensity'})
        chart1.set_style(11)
        chart1.set_size({'x_scale':1.55,'y_scale':1.6})
        worksheet.insert_chart('I2', chart1)


        chart2 = workbook.add_chart({'type': 'scatter'})
        chart2.add_series({
            'name':       'Data',
            'categories': "".join("="+energy+"!$E$3:$E$"+str(2+len(y_prof[0]))),
            'values':     "".join("="+energy+"!$F$3:$F$"+str(2+len(y_prof[1]))),
            'line': {'color':'red', 'width': 1,},
            'marker': {'type':'none'},
        })
        chart2.add_series({
            'name':       'Model',
            'categories': "".join("="+energy+"!$E$3:$E$"+str(2+len(y_prof[0]))),
            'values':     "".join("="+energy+"!$G$3:$G$"+str(2+len(y_model[1]))),
            'line': {'color':'blue', 'width': 1,},
            'marker': {'type':'none'},
        })
        chart2.set_title ({'name': 'Y Profile'})
        chart2.set_x_axis({'name': 'Y_Coordinate (mm)'})
        chart2.set_y_axis({'name': 'Relative intensity'})
        chart2.set_style(11)
        chart2.set_size({'x_scale':1.55,'y_scale':1.6})
        worksheet.insert_chart('I25', chart2)

    workbook.close()
if __name__ == '__main__':
    main()
