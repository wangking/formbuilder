from formbuilder import tablebuilder
from formbuilder import tableform
from formbuilder import validators

table = tablebuilder.Table(
    "test_table",
    tablebuilder.Field("name","string",default="hello"),
    tablebuilder.Field("age","integer",default=20),
    tablebuilder.Field("mysex","boolean",default=False,comment="select your sex"),
    tablebuilder.Field("friends","list::string",default=["huaiyu","jim"],comment="select your friends")
)

table.age.requires = validators.IS_INT_IN_RANGE(18,25,error_message = "your age is not suitable for me")
table.friends.requires = validators.IS_IN_SET([("huaiyu","wang huaiyu"),("tim", "wang tim"),("jim", "jim green")],multiple=True)
vars = {"_id":"dfgdg","name":"huaiyu", "age":20, "mysql":False, "friends":["huaiyu","jim"]}
form = tableform.FORMBUILDER(table, vars, formstyle="divs")
print form.accepts(vars)
print form.vars
