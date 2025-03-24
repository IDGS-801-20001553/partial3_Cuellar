from wtforms import Form, StringField, IntegerField, SelectField, BooleanField, validators, PasswordField
from wtforms.validators import DataRequired

class PedidoForm(Form):
    nombre = StringField('Nombre Completo', validators=[DataRequired(message='El nombre es requerido')])
    direccion = StringField('Dirección', validators=[DataRequired(message='La dirección es requerida')])
    telefono = StringField('Teléfono', validators=[DataRequired(message='El teléfono es requerido')])

    tamaño = SelectField('Tamaño', choices=[('chica', 'Chica'), ('mediana', 'Mediana'), ('grande', 'Grande')], 
                        validators=[DataRequired(message='El tamaño es requerido')])

    
    jamon = BooleanField('Jamón')
    pina = BooleanField('Piña')
    champiñones = BooleanField('Champiñones')

    cantidad = IntegerField('Cantidad', validators=[DataRequired(message='La cantidad es requerida')])

class LoginForm(Form):
    username = StringField('Nombre de usuario', [validators.DataRequired(message='El usuario es requerido')])
    password = PasswordField('Contraseña', [validators.DataRequired(message='La contraseña es requerida')])