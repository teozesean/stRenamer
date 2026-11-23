#------------------------------------------------------------------Note------------------------------------------------------------------#
#Name: stRenamer
#Version: 2.0
#Author: Sean Teo
#Created: 24th October 2018
#Last Update: 23rd November 2026
#---1)Name Preview: Displays the original and new name before the user decides to activate the function.
#                   Updates with 'Refresh Preview' button or editing any text fields.
#
#---2)Category Selection: Filter affected objects in the following lists: 'Selected', 'Hierarchy' and 'All'.
#                         'Duplicates' button identifies total number of objects with the same name.
#
#---3)Rename Variable: To include variables like [A-Z], [a-z], [0-9].
#                      Alphabets have 'Sequence' option and [AA-ZZ],[aa-zz] format if selection exceeds 26 objects.(Max of 702 objects at once)
#                      Numbers have 'Start No.' and 'Padding' options.
#                      'Rename' button can simultaneously add Prefix and Suffix, if text is found in their respected text fields.
#
#---4)Prefix & Suffix: Adds Prefix & Suffix individually.
#
#---5)Search & Replace: Similar to Maya's built in Search & Replace with minor tweaks.
#                       Refer will run the first selection's name through 'Search & Replace' and the result will be the second selected object's new name.

#-----------------------------------------------------------------Window-----------------------------------------------------------------#

#---------------Rename Tool---------------#
import sys
from pathlib import Path

import maya.cmds as cmds

_FILE = globals().get("__file__")
_FOLDER = str(Path(_FILE).resolve().parent) if _FILE else ""
if _FOLDER and _FOLDER not in sys.path:
    sys.path.insert(0, _FOLDER)

import stRenamer_UTIL as rename_util

WINDOW_NAME = "renameToolwindow"


# -----------------------------------------------------------------------------
# UI callbacks
# -----------------------------------------------------------------------------


def reset_to_default(*args) -> None:
    rename_util.reset_to_default()


def refresh_current_name(*args) -> None:
    rename_util.refresh_preview()


def refresh_new_name(*args) -> None:
    rename_util.refresh_preview()


def duplicate_selection(*args) -> None:
    if cmds.radioButtonGrp("categoryCommand", query=True, select=True) == 4:
        rename_util.select_duplicates()


def variable_visibility(*args) -> None:
    rename_util.variable_visibility()
    rename_util.refresh_preview()


def rename_selected(*args) -> None:
    rename_util.rename_selected()


def add_prefix(*args) -> None:
    rename_util.add_prefix()


def add_suffix(*args) -> None:
    rename_util.add_suffix()


def replace_name(*args) -> None:
    rename_util.replace_name()


# -----------------------------------------------------------------------------
# Window construction — importing this module only defines the UI.
# Call show_rename_tool() to build the window the first time and to
# show the existing window on later calls.
# -----------------------------------------------------------------------------


def build_window() -> None:
    """Build the Rename Tool window from scratch and show it.

    Every control creation statement lives here, with its control
    names preserved, so the file is safe to import, reload, and
    test without a window appearing. Any existing window of the
    same name is deleted first.
    """
    if cmds.window(WINDOW_NAME, exists=True):
        cmds.deleteUI(WINDOW_NAME)

    #-------------Create Window---------------#
    cmds.window(
        WINDOW_NAME,
        title="stRenamer",
        s=False,
        mnb=True,
        mxb=False,
        restoreCommand=refresh_current_name,
    )
    cmds.columnLayout('renameTool_col00', width = 420, height = 600)
    cmds.rowColumnLayout('reset_col00', numberOfColumns=2, columnWidth=[(1,150), (2,270)], p='renameTool_col00')
    cmds.button('reset_btn00',label='Reset to Default', w=150,h=20,bgc=(0.3,0.51,0.3),command=reset_to_default, p='reset_col00')
    cmds.button('refresh_btn00',label='Refresh Preview', w=150,h=20,bgc=(0.3,0.5,0.51),command=refresh_current_name, p='reset_col00')

    #---------------Preview Name Result---------------#
    cmds.frameLayout(label='Name Preview',h=20, w=420, p='renameTool_col00')
    cmds.rowColumnLayout('Preview_col00', numberOfColumns=2, columnWidth=[(1,150), (2,270)], p='renameTool_col00')
    cmds.text('Current Name :', h=30, bgc= (0.2,0.2,0.2),p='Preview_col00')
    cmds.textField('Current_Name_Result', h=30, ed= False, bgc=(0.22,0.22,0.22),font = 'boldLabelFont',p='Preview_col00')
    cmds.text('New Name :', h=30, bgc= (0.2,0.2,0.2), p='Preview_col00')
    cmds.textField('New_Name_Result', h=30, ed=False, bgc=(0.22,0.22,0.22),font = 'boldLabelFont',p='Preview_col00')

    #---------------Category Selection---------------#
    cmds.frameLayout(label='Category Selection',h=20, w= 420, p='renameTool_col00')
    cmds.radioButtonGrp('categoryCommand', label='Category :  ', sl=1, labelArray4=[ ' Selected ', ' Hierarchy ', ' All ', ' Duplicates '],cc=duplicate_selection, numberOfRadioButtons=4, columnWidth5 = [90,90,90,55,95],height = 40, p='renameTool_col00')

    #---------------Variable---------------#
    cmds.columnLayout('Variable_col00', p = 'renameTool_col00')
    cmds.frameLayout('Variable_col01', w=420, label='Rename Variable', p='Variable_col00')
    cmds.separator('Variable_separator00', st='none', h= 10, p='Variable_col00')
    cmds.radioButtonGrp('Variable_BtnGrp', label = 'Variable : ',sl=1, labelArray4=[ ' None ', ' A - Z ', ' a - z ', ' 0 - 9 '], cc=variable_visibility, numberOfRadioButtons=4, columnWidth5= [100,65,65,65,65], height = 20, p='Variable_col00')
    cmds.separator('Variable_separator01',st='none', h= 10, p='Variable_col00')
    cmds.rowColumnLayout('Variable_col02', numberOfColumns=2, columnWidth=[(1,200), (2,220)],vis = 0, p='Variable_col00')
    cmds.optionMenuGrp('upper_optMenuGrp', label = 'Alphabet : ', p='Variable_col02', cw2 = [100,100], h= 40, vis = 0, cc=refresh_new_name)

    charUpper = ('A','B','C','D','E','F','G','H','I','J','K','L','M','N','O','P','Q','R','S','T','U','V','W','X','Y','Z')
    for i in charUpper:
        cmds.menuItem(l=i)

    cmds.checkBox('uppercase_checkbox00',v=1, label = 'Sequence Letters', cc=refresh_new_name)

    cmds.rowColumnLayout('Variable_col03', numberOfColumns=2, vis = 0, columnWidth=[(1,200), (2,220)], p='Variable_col00')
    cmds.optionMenuGrp('lower_optMenuGrp', label = 'Alphabet : ', p='Variable_col03', cw2 = [100,100], h= 40, vis = 0, cc=refresh_new_name)

    charLower = ('a','b','c','d','e','f','g','h','i','j','k','l','m','n','o','p','q','r','s','t','u','v','w','x','y','z')
    for i in charLower:
        cmds.menuItem(l=i)

    cmds.checkBox('lowercase_checkbox00',label = 'Sequence Letters', v=1, p='Variable_col03', cc=refresh_new_name)

    cmds.intFieldGrp('padding_tf', numberOfFields =2, l = 'Start No :', el = ' Padding', value1 = 1, value2 = 2, ct4 = ['left', 'left', 'left','left'], co4 = [50, -40, 0,0], vis = 0, h= 42, p='Variable_col00', cc=refresh_new_name)
    cmds.textFieldGrp('Variable_tfGrp', label = ' New Name : ', text = '', tcc=refresh_new_name, cw2 = [ 100, 250], h = 20, p='Variable_col00')
    cmds.separator('Variable_separator02',st='none', h= 15, p='Variable_col00')
    cmds.button('Rename_btn00', label='Rename', w=420, h=40, bgc=(0.3,0.5,0.5), command=rename_selected, p='Variable_col00')
    cmds.separator('Variable_separator03',st='none', h= 15, p='Variable_col00')

    #---------------Prefix & Suffix---------------#
    cmds.columnLayout('PrefixSuffix_col00', p = 'renameTool_col00')
    cmds.frameLayout(label='Prefix  &  Suffix',h=20, w=420,p='PrefixSuffix_col00')
    cmds.separator(st='none', h=15, p='PrefixSuffix_col00')
    cmds.rowColumnLayout('PrefixSuffix_col01',numberOfColumns=3, columnWidth=[(1, 200), (2,20), (3, 200)], p='PrefixSuffix_col00')
    cmds.button('Prefix_btn00',label='Add Prefix',w=200,h=30,bgc=(0.3,0.5,0.4),command=add_prefix, p='PrefixSuffix_col01')
    cmds.separator(st='none', p='PrefixSuffix_col01')
    cmds.button('Suffix_btn00',label='Add Suffix',w=200,h=30,bgc=(0.3,0.5,0.4),command=add_suffix, p='PrefixSuffix_col01')
    cmds.textField('Prefix_tf00',width=200, height = 20, tcc=refresh_new_name,p='PrefixSuffix_col01')
    cmds.separator(st='none', p='PrefixSuffix_col01')
    cmds.textField('Suffix_tf00',width=200, height = 20, tcc=refresh_new_name, p='PrefixSuffix_col01')
    cmds.separator(st='none', h=10, p='PrefixSuffix_col00')

    #---------------Search & Replace---------------#
    cmds.columnLayout('SR_col00', p='renameTool_col00')
    cmds.frameLayout(label='Search  &  Replace',h=20, w=420, p='SR_col00')
    cmds.separator(st='none', h= 15, p='SR_col00')
    cmds.rowColumnLayout(
        'Search_row00',
        numberOfColumns=3,
        columnWidth=[(1, 350), (2, 8), (3, 62)],
        p='SR_col00',
    )
    cmds.textFieldGrp(
        'Search_tf00',
        label=' Search for : ',
        text='',
        tcc=refresh_new_name,
        cw2=[95, 255],
        p='Search_row00',
    )
    cmds.separator(
        style='none',
        width=8,
        parent='Search_row00',
    )
    cmds.checkBox(
        'refer_checkbox00',
        label=' Refer',
        value=False,
        parent='Search_row00',
        width=62,
    )
    cmds.separator(st='none', h= 10, p='SR_col00')
    cmds.textFieldGrp ('Replace_tf00', label = ' Replace with : ', text = '', tcc=refresh_new_name, cw2 = [95, 255], p='SR_col00')
    cmds.separator(st='none', h= 15, p='SR_col00')
    cmds.button('Variable_btn01', l='Replace',w=420,h=40,bgc=(0.3,0.5,0.5),c=replace_name, p='SR_col00')

    #-----------------Show Window-----------------#
    cmds.showWindow(WINDOW_NAME)
    rename_util.refresh_preview()


def show_rename_tool() -> None:
    """Launch the Rename Tool: build a new window or show the existing one."""
    if cmds.window(WINDOW_NAME, exists=True):
        cmds.showWindow(WINDOW_NAME)
        rename_util.refresh_preview()
    else:
        build_window()
