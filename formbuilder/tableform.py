#!/usr/bin/env python
# -*- coding: utf-8 -*-

from html import XML, SPAN, TAG, A, DIV, UL, LI, TEXTAREA, BR, IMG, SCRIPT
from html import FORM, INPUT, LABEL, OPTION, SELECT
from html import TABLE, THEAD, TBODY, TR, TD, TH
from storage import Storage
from hashfunc import md5_hash
from validators import IS_EMPTY_OR
import copy
import urllib
import re
import cStringIO


table_field = re.compile('[\w_]+\.[\w_]+')
widget_class = re.compile('^\w*')

def safe_int(x):
    try:
        return int(x)
    except ValueError:
        return 0

def safe_float(x):
    try:
        return float(x)
    except ValueError:
        return 0

class FormWidget(object):
    """
    helper for FORMBUILDER to generate form input fields (widget),
    related to the fieldtype
    """

    @staticmethod
    def _attributes(field, widget_attributes, **attributes):
        """
        helper to build a common set of attributes

        :param field: the field involved, some attributes are derived from this
        :param widget_attributes:  widget related attributes
        :param attributes: any other supplied attributes
        """
        attr = dict(
            _id = '%s_%s' % (field._tablename, field.name),
            _class = widget_class.match(str(field.type)).group(),
            _name = field.name,
            requires = field.requires,
            )
        attr.update(widget_attributes)
        attr.update(attributes)
        return attr

    @staticmethod
    def widget(field, value, **attributes):
        """
        generates the widget for the field.

        When serialized, will provide an INPUT tag:

        - id = tablename_fieldname
        - class = field.type
        - name = fieldname

        :param field: the field needing the widget
        :param value: value
        :param attributes: any other attributes to be applied
        """

        raise NotImplementedError

class StringWidget(FormWidget):

    @staticmethod
    def widget(field, value, **attributes):
        """
        generates an INPUT text tag.

        see also: :meth:`FormWidget.widget`
        """
        if value:
            if isinstance(value, unicode):
                value = value.encode("utf-8")
        default = dict(
            _type = 'text',
            value = (value!=None and str(value)) or '',
            )
        attr = StringWidget._attributes(field, default, **attributes)

        return INPUT(**attr)

class HiddenWidget(FormWidget):

    @staticmethod
    def widget(field, value, **attributes):
        """
        generates an INPUT text tag.

        see also: :meth:`FormWidget.widget`
        """
        if value:
            if isinstance(value, unicode):
                value = value.encode("utf-8")
        default = dict(
            _type = 'hidden',
            value = (value!=None and str(value)) or '',
            )
        attr = StringWidget._attributes(field, default, **attributes)

        return INPUT(**attr)


class IntegerWidget(StringWidget):

    pass


class DoubleWidget(StringWidget):

    pass


class DecimalWidget(StringWidget):

    pass


class TimeWidget(StringWidget):

    pass


class DateWidget(StringWidget):

    pass


class DatetimeWidget(StringWidget):

    pass


class TextWidget(FormWidget):

    @staticmethod
    def widget(field, value, **attributes):
        """
        generates a TEXTAREA tag.

        see also: :meth:`FormWidget.widget`
        """

        default = dict(
            value = value,
            )
        attr = TextWidget._attributes(field, default, **attributes)

        return TEXTAREA(**attr)


class BooleanWidget(FormWidget):

    @staticmethod
    def widget(field, value, **attributes):
        """
        generates an INPUT checkbox tag.

        see also: :meth:`FormWidget.widget`
        """

        default=dict(
            _type='checkbox',
            value=value,
            )
        attr = BooleanWidget._attributes(field, default, **attributes)

        return INPUT(**attr)


class OptionsWidget(FormWidget):

    @staticmethod
    def has_options(field):
        """
        checks if the field has selectable options

        :param field: the field needing checking
        :returns: True if the field has options
        """

        return hasattr(field.requires, 'options')

    @staticmethod
    def widget(field, value, **attributes):
        """
        generates a SELECT tag, including OPTIONs (only 1 option allowed)

        see also: :meth:`FormWidget.widget`
        """
        default = dict(
            value=value,
            )
        attr = OptionsWidget._attributes(field, default, **attributes)

        requires = field.requires
        if not isinstance(requires, (list, tuple)):
            requires = [requires]
        if requires:
            if hasattr(requires[0], 'options'):
                options = requires[0].options()
            else:
                raise SyntaxError, 'widget cannot determine options of %s' \
                    % field
        opts = [OPTION(v, _value=k) for (k, v) in options]

        return SELECT(*opts, **attr)

class ListWidget(StringWidget):
    @staticmethod
    def widget(field,value,**attributes):
        _id = '%s_%s' % (field._tablename, field.name)
        _name = field.name
        if field.type=='list:integer': _class = 'integer'
        else: _class = 'string'
        items=[LI(INPUT(_id=_id,_class=_class,_name=_name,value=v,hideerror=True)) \
                   for v in value or ['']]
        script=SCRIPT("""
// from http://refactormycode.com/codes/694-expanding-input-list-using-jquery
(function(){
jQuery.fn.grow_input = function() {
  return this.each(function() {
    var ul = this;
    jQuery(ul).find(":text").after('<a href="javascript:void(0)>+</a>').keypress(function (e) { return (e.which == 13) ? pe(ul) : true; }).next().click(function(){ pe(ul) });
  });
};
function pe(ul) {
  var new_line = ml(ul);
  rel(ul);
  new_line.appendTo(ul);
  new_line.find(":text").focus();
  return false;
}
function ml(ul) {
  var line = jQuery(ul).find("li:first").clone(true);
  line.find(':text').val('');
  return line;
}
function rel(ul) {
  jQuery(ul).find("li").each(function() {
    var trimmed = jQuery.trim(jQuery(this.firstChild).val());
    if (trimmed=='') jQuery(this).remove(); else jQuery(this.firstChild).val(trimmed);
  });
}
})();
jQuery(document).ready(function(){jQuery('#%s_grow_input').grow_input();});
""" % _id)
        attributes['_id']=_id+'_grow_input'
        return TAG[''](UL(*items,**attributes),script)


class MultipleOptionsWidget(OptionsWidget):

    @staticmethod
    def widget(field, value, size=5, **attributes):
        """
        generates a SELECT tag, including OPTIONs (multiple options allowed)

        see also: :meth:`FormWidget.widget`

        :param size: optional param (default=5) to indicate how many rows must
            be shown
        """

        attributes.update(dict(_size=size, _multiple=True))

        return OptionsWidget.widget(field, value, **attributes)


class RadioWidget(OptionsWidget):

    @staticmethod
    def widget(field, value, **attributes):
        """
        generates a TABLE tag, including INPUT radios (only 1 option allowed)

        see also: :meth:`FormWidget.widget`
        """

        attr = OptionsWidget._attributes(field, {}, **attributes)

        requires = field.requires
        if not isinstance(requires, (list, tuple)):
            requires = [requires]
        if requires:
            if hasattr(requires[0], 'options'):
                options = requires[0].options()
            else:
                raise SyntaxError, 'widget cannot determine options of %s' \
                    % field

        options = [(k, v) for k, v in options if str(v)]
        opts = []
        cols = attributes.get('cols',1)
        totals = len(options)
        mods = totals%cols
        rows = totals/cols
        if mods:
            rows += 1

        for r_index in range(rows):
            tds = []
            for k, v in options[r_index*cols:(r_index+1)*cols]:
                tds.append(TD(INPUT(_type='radio', _name=field.name,
                         requires=attr.get('requires',None),
                         hideerror=True, _value=k,
                         value=value), v))
            opts.append(TR(tds))

        if opts:
            opts[-1][0][0]['hideerror'] = False
        return TABLE(*opts, **attr)


class CheckboxesWidget(OptionsWidget):

    @staticmethod
    def widget(field, value, **attributes):
        """
        generates a TABLE tag, including INPUT checkboxes (multiple allowed)

        see also: :meth:`FormWidget.widget`
        """

        # was values = re.compile('[\w\-:]+').findall(str(value))
        values = not isinstance(value,(list,tuple)) and [value] or value

        attr = OptionsWidget._attributes(field, {}, **attributes)

        requires = field.requires
        if not isinstance(requires, (list, tuple)):
            requires = [requires]
        if requires:
            if hasattr(requires[0], 'options'):
                options = requires[0].options()
            else:
                raise SyntaxError, 'widget cannot determine options of %s' \
                    % field

        options = [(k, v) for k, v in options if k!='']
        opts = []
        cols = attributes.get('cols',1)
        totals = len(options)
        mods = totals%cols
        rows = totals/cols
        if mods:
            rows += 1

        for r_index in range(rows):
            tds = []
            for k, v in options[r_index*cols:(r_index+1)*cols]:
                tds.append(TD(INPUT(_type='checkbox', _name=field.name,
                         requires=attr.get('requires',None),
                         hideerror=True, _value=k,
                         value=(k in values)), v))
            opts.append(TR(tds))

        if opts:
            opts[-1][0][0]['hideerror'] = False
        return TABLE(*opts, **attr)


class PasswordWidget(FormWidget):

    DEFAULT_PASSWORD_DISPLAY = 8*('*')

    @staticmethod
    def widget(field, value, **attributes):
        """
        generates a INPUT password tag.
        If a value is present it will be shown as a number of '*', not related
        to the length of the actual value.

        see also: :meth:`FormWidget.widget`
        """

        default=dict(
            _type='password',
            _value=(value and PasswordWidget.DEFAULT_PASSWORD_DISPLAY) or '',
            )
        attr = PasswordWidget._attributes(field, default, **attributes)

        return INPUT(**attr)


class UploadWidget(FormWidget):

    DEFAULT_WIDTH = '150px'
    ID_DELETE_SUFFIX = '__delete'
    GENERIC_DESCRIPTION = 'file'
    DELETE_FILE = 'delete'

    @staticmethod
    def widget(field, value, download_url=None, **attributes):
        """
        generates a INPUT file tag.

        Optionally provides an A link to the file, including a checkbox so
        the file can be deleted.
        All is wrapped in a DIV.

        see also: :meth:`FormWidget.widget`

        :param download_url: Optional URL to link to the file (default = None)
        """
        default=dict(
            _type='file',
            )
        attr = UploadWidget._attributes(field, default, **attributes)

        inp = INPUT(**attr)

        if download_url != None and value:
            url = download_url + value
            (br, image) = ('', '')
            if UploadWidget.is_image(value):
                br = BR()
                image = IMG(_src = url, _width = UploadWidget.DEFAULT_WIDTH)

            requires = attr["requires"]
            if requires == [] or isinstance(requires, IS_EMPTY_OR):
                inp = DIV(inp, '[',
                          A(UploadWidget.GENERIC_DESCRIPTION, _href = url),
                          '|',
                          INPUT(_type='checkbox',
                                _name=field.name + UploadWidget.ID_DELETE_SUFFIX),
                          UploadWidget.DELETE_FILE,
                          ']', br, image)
            else:
                inp = DIV(inp, '[',
                          A(UploadWidget.GENERIC_DESCRIPTION, _href = url),
                          ']', br, image)
        return inp

    @staticmethod
    def represent(field, value, download_url=None):
        """
        how to represent the file:

        - with download url and if it is an image: <A href=...><IMG ...></A>
        - otherwise with download url: <A href=...>file</A>
        - otherwise: file

        :param field: the field
        :param value: the field value
        :param download_url: url for the file download (default = None)
        """

        inp = UploadWidget.GENERIC_DESCRIPTION

        if download_url != None and value:
            url = download_url + value
            if UploadWidget.is_image(value):
                inp = IMG(_src = url, _width = UploadWidget.DEFAULT_WIDTH)
            inp = A(inp, _href = url)

        return inp

    @staticmethod
    def is_image(value):
        """
        Tries to check if the filename provided references to an image

        Checking is based on filename extension. Currently recognized:
           gif, png, jp(e)g, bmp

        :param value: filename
        """

        extension = value.split('.')[-1].lower()
        if extension in ['gif', 'png', 'jpg', 'jpeg', 'bmp']:
            return True
        return False


class FORMBUILDER(FORM):

    """
    FORMBUILDER is used to map a table (and a current record) into an HTML form

    given a SQLTable stored in db.table

    generates an insert form::

        FORMBUILDER(db.table)

    generates an update form::

        record=db.table[some_id]
        FORMBUILDER(db.table, record)

    generates an update with a delete button::

        FORMBUILDER(db.table, record, deletable=True)

    if record is an int::

        record=db.table[record]

    optional arguments:

    :param fields: a list of fields that should be placed in the form,
        default is all.
    :param labels: a dictionary with labels for each field, keys are the field
        names.
    :param col3: a dictionary with content for an optional third column
            (right of each field). keys are field names.
            see controller appadmin.py for examples
    :param upload: the URL of a controller/function to download an uploaded file
            see controller appadmin.py for examples

    any named optional attribute is passed to the <form> tag
            for example _class, _id, _style, _action, _method, etc.

    """

    # usability improvements proposal by fpp - 4 May 2008 :
    # - correct labels (for points to field id, not field name)
    # - add label for delete checkbox
    # - add translatable label for record ID
    # - add third column to right of fields, populated from the col3 dict

    widgets = Storage(dict(
        string = StringWidget,
        text = TextWidget,
        hidden = HiddenWidget,
        password = PasswordWidget,
        integer = IntegerWidget,
        double = DoubleWidget,
        decimal = DecimalWidget,
        time = TimeWidget,
        date = DateWidget,
        datetime = DatetimeWidget,
        upload = UploadWidget,
        boolean = BooleanWidget,
        blob = None,
        options = OptionsWidget,
        multiple = CheckboxesWidget,
        radio = RadioWidget,
        checkboxes = CheckboxesWidget,
        list = ListWidget,
        ))

    FIELDNAME_REQUEST_DELETE = 'delete_this_record'
    FIELDKEY_DELETE_RECORD = 'delete_record'
    ID_LABEL_SUFFIX = '__label'
    ID_ROW_SUFFIX = '__row'

    def __init__(
        self,
        table,
        record = None,
        deletable = False,
        download = "",
        upload = None,
        fields = None,
        labels = None,
        col3 = {},
        submit_button = 'Submit',
        delete_label = 'Check to delete:',
        showid = True,
        readonly = False,
        comments = True,
        keepopts = [],
        ignore_rw = False,
        formstyle = 'divs',
        record_pk_name = '_id',
        tabs = [],
        **attributes
        ):
        """
        FORMBUILDER(db.table,
               record=None,
               fields=['name'],
               labels={'name': 'Your name'},
        """
        self.table = table
        if record:
            for itm in record:
                if isinstance(record[itm],(list,tuple)):
                    if not (itm in self.table.fields and self.table[itm].type.startswith("list::")):
                        record[itm] = record[itm][-1]
        self.custom_file = upload
        self.ignore_rw = ignore_rw
        self.formstyle = formstyle
        self.record_pk_name = record_pk_name
        nbsp = XML('&nbsp;') # Firefox2 does not display fields with blanks
        attributes.update({"_id":"hyform_%s"%self.table._tablename})
        FORM.__init__(self, *[], **attributes)
        ofields = fields

        # if no fields are provided, build it from the provided table
        # will only use writable or readable fields, unless forced to ignore
        if fields == None:
            fields = [f.name for f in table if (ignore_rw or f.writable or f.readable)]

        self.record = record

        self.field_parent = {}
        xfields = {}
        xfields_keys = []
        self.fields = fields
        self.custom = Storage()
        self.custom.dspval = Storage()
        self.custom.inpval = Storage()
        self.custom.label = Storage()
        self.custom.comment = Storage()
        self.custom.widget = Storage()

        for fieldname in self.fields:
            if fieldname.find('.') >= 0:
                continue

            field = self.table[fieldname]
            comment = None

            if comments:
                comment = col3.get(fieldname, field.comment)
            if comment == None:
                comment = ''
            self.custom.comment[fieldname] = comment

            if labels != None and fieldname in labels:
                label = labels[fieldname]
                colon = ''
            else:
                label = field.label
                colon = ': '
            self.custom.label[fieldname] = label

            field_id = '%s_%s' % (table._tablename, fieldname)

            label = LABEL(label, colon, _for=field_id,
                          _id=field_id+FORMBUILDER.ID_LABEL_SUFFIX)

            row_id = field_id + FORMBUILDER.ID_ROW_SUFFIX

            if readonly and not ignore_rw and not field.readable:
                continue

            if record:
                default = record.get(fieldname, field.default)
            else:
                default = field.default

            cond = readonly or \
                (not ignore_rw and not field.writable and field.readable)

            if default and not cond:
                default = field.formatter(default)
            dspval = default
            inpval = default

            if cond:

                # ## if field.represent is available else
                # ## ignore blob and preview uploaded images
                # ## format everything else

                if field.represent:
                    inp = field.represent(default)
                elif field.type in ['blob']:
                    continue
                elif field.type == 'upload':
                    inp = UploadWidget.represent(field, default, download)
                elif field.type == 'boolean':
                    inp = self.widgets.boolean.widget(field, default, _disabled=True)
                else:
                    inp = field.formatter(default)
            elif field.type == 'upload':
                if hasattr(field, 'widget') and field.widget:
                    inp = field.widget(field, default, download)
                else:
                    inp = self.widgets.upload.widget(field, default, download)
            elif hasattr(field, 'widget') and field.widget:
                inp = field.widget(field, default)
            elif field.type == 'boolean':
                inp = self.widgets.boolean.widget(field, default)
                if default:
                    inpval = 'checked'
                else:
                    inpval = ''
            elif OptionsWidget.has_options(field):
                if not field.requires.multiple:
                    inp = self.widgets.options.widget(field, default)
                else:
                    inp = self.widgets.multiple.widget(field, default)
                if fieldname in keepopts:
                    inpval = TAG[''](*inp.components)
            elif field.type.startswith('list:'):
                inp = self.widgets.list.widget(field,default)
            elif field.type == 'text':
                inp = self.widgets.text.widget(field, default)
            elif field.type == 'hidden':
                inp = self.widgets.hidden.widget(field, default)
            elif field.type == 'password':
                inp = self.widgets.password.widget(field, default)
                if self.record:
                    dspval = PasswordWidget.DEFAULT_PASSWORD_DISPLAY
                else:
                    dspval = ''
            elif field.type == 'blob':
                continue
            else:
                inp = self.widgets.string.widget(field, default)
            xfields_keys.append(fieldname)
            xfields[fieldname] = (row_id,label,inp,comment)
            self.custom.dspval[fieldname] = dspval or nbsp
            self.custom.inpval[fieldname] = inpval or ''
            self.custom.widget[fieldname] = inp


        # when writable, add submit button
        self.custom.submit = ''
        if not readonly:
            widget = INPUT(_type='submit',_class="submit",
                           _value=submit_button,
                           _id = "submit_%s"%self.table._tablename )
            self.custom.submit = widget
        # if a record is provided and found
        # make sure it's id is stored in the form
        if record:
            if not self['hidden']:
                self['hidden'] = {}

        (begin, end) = self._xml()
        self.custom.begin = XML("<%s %s>" % (self.tag, begin))
        self.custom.end = XML("%s</%s>" % (end, self.tag))

        table = TAG['']()
        if formstyle == 'divs':
            # tabs = [
            #          {"tabname":"personal","caption":"个人信息","fields":["login","age"]},
            #          {"tabname":"comp","caption":"公司信息","fields":["login","age"]},
            #          {"tabname":"gf","caption":"朋友信息","fields":["login","age"]},
            #        ]
            if tabs:
                tab_headers = UL()
                tab_bodys = []
                
                for i, tab in enumerate(tabs):
                    tbody = DIV(_id="body_%s"%(tab.get("tabname","")))
                    if i == 0:
                        li = LI(tab.get("caption",""),_class="active", _id="tab_%s"%(tab.get("tabname","")))
                        tbody['_class'] = "active"
                    else:
                        li = LI(tab.get("caption",""),_style="display:none;",_id="tab_%s"%(tab.get("tabname","")))
                        tbody['_style'] = "display:none;"
                    tab_headers.append(li)
                    for f in tab.get("fields",[]):
                        if f in xfields_keys:
                            id,a,b,c = xfields[f]
                            div_b = self.field_parent[id] = DIV(b,_class='w2p_fw')
                            tbody.append(DIV(DIV(a,_class='w2p_fl'),div_b,DIV(c,_class='w2p_fc'),_id=id, _class="fb_row"))
                    tab_bodys.append(tbody)                  
                tab_headers = DIV(tab_headers, _id="tab_headers_%s"%self.table._tablename)
                tab_bodys = DIV(tab_bodys, _id="tab_bodys_%s"%self.table._tablename)
                table.append(DIV(tab_headers, tab_bodys))
            else:
                for d in xfields_keys:
                    id,a,b,c = xfields[d]
                    div_b = self.field_parent[id] = DIV(b,_class='w2p_fw')
                    table.append(DIV(DIV(a,_class='w2p_fl'),
                                 div_b,
                                 DIV(c,_class='w2p_fc'),_id=id,_class="fb_row"))

        self.components = [table, self.custom.submit]

    def accepts(
        self,
        request_vars,
        formname='%(tablename)s_%(record_id)s',
        keepvalues=False,
        onvalidation=None,
        hideerror=False,
        ):

        """
        similar FORM.accepts but also does insert, update or delete in SQLDB.
        but if detect_record_change == True than:
          form.record_changed = False (record is properly validated/submitted)
          form.record_changed = True (record cannot be submitted because changed)
        elseif detect_record_change == False than:
          form.record_changed = None
        """
        # implement logic to detect whether record exist but has been modified
        # server side
        _vars_ = {}
        request_vars = copy.deepcopy(request_vars)
        for itm in request_vars:
            if isinstance(request_vars[itm],(list,tuple)):
                if not (str(itm) in self.table.fields and str(self.table[itm].type).startswith("list::")):
                    request_vars[itm] = request_vars[itm][-1]
        if self.record:
            (formname_id, record_id) = ( self.record.get(self.record_pk_name, None), 
                                         request_vars.get(self.record_pk_name, None))
            keepvalues = True
        else:
            (formname_id, record_id) = ('create', None)

        
        if formname:
            formname = formname % dict(tablename = self.table._tablename,
                                       record_id = formname_id)


        for fieldname in self.fields:
            field = self.table[fieldname]
            requires = field.requires or []
            if not isinstance(requires, (list, tuple)):
                requires = [requires]

        # ## END

        fields = {}
        for key in self.vars:
            fields[key] = self.vars[key]

        ret = FORM.accepts(
            self,
            request_vars,
            formname,
            keepvalues,
            onvalidation,
            hideerror=hideerror,
            )

        if not ret and self.record and self.errors:
            ### if there are errors in update mode
            # and some errors refers to an already uploaded file
            # delete error if
            # - user not trying to upload a new file
            # - there is existing file and user is not trying to delete it
            # this is because removing the file may not pass validation
            for key in self.errors.keys():
                if self.table[key].type == 'upload' \
                        and request_vars.get(key,None) in (None,'') \
                        and self.record[key] \
                        and not key+UploadWidget.ID_DELETE_SUFFIX in request_vars:
                    del self.errors[key]
            if not self.errors:
                ret = True

        requested_delete = \
            request_vars.get(self.FIELDNAME_REQUEST_DELETE, False)

        self.custom.end = TAG[''](self.hidden_fields(), self.custom.end)

        auch = record_id and self.errors and requested_delete

        # auch is true when user tries to delete a record
        # that does not pass validation, yet it should be deleted

        if not ret and not auch:
            for fieldname in self.fields:
                field = self.table[fieldname]
                ### this is a workaround! widgets should always have default not None!
                if not field.widget and field.type.startswith('list:') and \
                        not OptionsWidget.has_options(field):
                    field.widget = self.widgets.list.widget
                if hasattr(field, 'widget') and field.widget and fieldname in request_vars:
                    if fieldname in self.vars:
                        value = self.vars[fieldname]
                    elif self.record:
                        value = self.record[fieldname]
                    else:
                        value = self.table[fieldname].default
                    row_id = '%s_%s%s' % (self.table,fieldname,FORMBUILDER.ID_ROW_SUFFIX)
                    widget = field.widget(field, value)
                    self.field_parent[row_id].components = [ widget ]
                    if not field.type.startswith('list:'):
                        self.field_parent[row_id]._traverse(False,hideerror)
                    self.custom.widget[ fieldname ] = widget
            return ret
        self.record_id = record_id

        if requested_delete and self.custom.deletable:
            self.errors.clear()
            for component in self.elements('input, select, textarea'):
                component['_disabled'] = True
            return True

        for fieldname in self.fields:
            if not fieldname in self.table:
                continue

            if not self.ignore_rw and not self.table[fieldname].writable:
                ### this happens because FROM has no knowledge of writable
                ### and thinks that a missing boolean field is a None
                if self.table[fieldname].type == 'boolean' and self.vars[fieldname]==None:
                    del self.vars[fieldname]
                continue

            field = self.table[fieldname]
            if field.type == 'id':
                continue
            if field.type == 'boolean':
                if self.vars.get(fieldname, False):
                    self.vars[fieldname] = fields[fieldname] = True
                else:
                    self.vars[fieldname] = fields[fieldname] = False
            elif field.type == 'password' and self.record\
                and request_vars.get(fieldname, None) == \
                    PasswordWidget.DEFAULT_PASSWORD_DISPLAY:
                continue  # do not update if password was not changed
            elif field.type == 'upload':
                if self.vars.get("%s__delete"%fieldname,False):
                    self.vars[fieldname] = ""
                    del self.vars["%s__delete"%fieldname]
                    continue
                if self.custom_file:
                    self.vars[fieldname] = self.custom_file(field, request_vars)
                else:
                    self.vars[fieldname] = field.store(request_vars.get(fieldname,""),request_vars.get("%s.original"%fieldname,""))
                continue
            elif fieldname in self.vars:
                fields[fieldname] = self.vars[fieldname]
            elif field.default == None and field.type!='blob':
                self.errors[fieldname] = 'no data'
                return False
            value = fields.get(fieldname,None)
            if field.type == 'list:string':
                if not isinstance(value,(tuple,list)):
                    fields[fieldname] = value and [value] or []
            elif field.type.startswith('list:'):
                if not isinstance(value,list):
                    fields[fieldname] = [safe_int(x) for x in (value and [value] or [])]
            elif field.type == 'integer':
                if value != None:
                    fields[fieldname] = safe_int(value)
            elif field.type == 'double':
                if value != None:
                    fields[fieldname] = safe_float(value)

        for fieldname in self.vars:
            if fieldname != 'id' and fieldname in self.table.fields\
                 and not fieldname in fields and not fieldname\
                 in request_vars:
                fields[fieldname] = self.vars[fieldname]
        return ret

if __name__ == '__main__':
    import tablebuilder
    frm = tablebuilder.Table(
        "huaiyu",
        tablebuilder.Field("name","string",default="hello"),
        tablebuilder.Field("age","integer",default=20),
        tablebuilder.Field("ages","hidden",default=20)
    )
    vars = {"name":"huaiyu", "age":40}
    form = FORMBUILDER(frm, vars, formstyle="divs")
    print form
