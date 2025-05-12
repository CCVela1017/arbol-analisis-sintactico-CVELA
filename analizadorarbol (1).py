import re


token_patron = {
  "KEYWORD": r'\b(if|else|for|while|print|return|int|float|void|input)\b',
  "IDENTIFIER": r'\b[a-zA-Z_][a-zA-Z0-9_]*\b',
  "NUMBER": r'\b\d+(\.\d+)?\b',
  "OPERATOR": r'<=|>=|==|!=|\+\+|--|\+=|-=|\*=|/=|&&|\|\||&|\||[+\-*/=<>]',  # \<=\>=\==\++\--\+=\-=\*=\/= # & && | ||
  "DELIMITER": r'[(),\";{}]',
  "WHITESPACE": r'\s+',
}


def identificar_tokens(texto):
  # Unir todos los patrones en un único patron utilizando grupos nombrados
  patron_general = '|'.join(f'(?P<{token}>{patron})' for token, patron in token_patron.items())
  patron_regex = re.compile(patron_general)
  token_encontrados = []
  for match_ in patron_regex.finditer(texto):
    for token, valor in match_.groupdict().items():
      if valor is not None and token != "WHITESPACE":
        token_encontrados.append((token, valor))

  return token_encontrados

# Analizador sintáctico
class Parser:
  def __init__(self, tokens):
    self.funcion_actual = ""
    self.ifcounter = {}
    self.whilecounter = {}
    self.forcounter = {}
    self.variables = []
    self.cad = []
    self.funciones = []
    self.params = []
    self.tokens = tokens
    self.pos = 0

  def obtener_token_actual(self):
    return self.tokens[self.pos] if self.pos < len(self.tokens) else None

  def coincidir(self, tipo_esperado):
    token_actual = self.obtener_token_actual()
    if token_actual and token_actual[0] == tipo_esperado:
      self.pos += 1
      return token_actual
    else:
      print(self.pos)
      print(token_actual)
      raise SyntaxError(f'Error Sintáctico: Se esperaba {tipo_esperado}, pero se encontró: {token_actual}')

  def parsear(self):
    # Punto de entrada: se espera una función
    while self.obtener_token_actual():
      print(self.obtener_token_actual())
      if self.obtener_token_actual()[1] == "int" or self.obtener_token_actual()[1] == "float" \
              or self.obtener_token_actual()[1] == "string" or self.obtener_token_actual()[1] == "void":
        self.funciones.append(self.funcion())

    namelist = []

    for funcion in self.funciones:
      namelist.append(funcion.nombre[1])

    if "main" not in namelist:
      raise SyntaxError("No se encontró la función main.")

    if self.funciones[len(self.funciones) - 1].nombre[1] != "main":
      raise SyntaxError("La función main no se encuentra al final del programa.")

    return NodoProgram(self.funciones);

  def funcion(self):
    # Gramatica para una función: int IDENTIFIER (, int IDENTIFIER) {cuerpo}
    tipo_retorno = self.coincidir("KEYWORD")  # Tipo de retorno (ej. int)
    nombre_funcion = self.coincidir("IDENTIFIER")  # Nombre de la función
    self.coincidir("DELIMITER")  # se espera un parentesis (
    parametros = []
    if not self.obtener_token_actual()[1] == ")":
      parametros = self.parametros()
    self.coincidir("DELIMITER")  # se espera un parentesis )
    self.coincidir("DELIMITER")  # se espera un corchete {
    self.funcion_actual = nombre_funcion[1]
    cuerpo = self.cuerpo()
    self.coincidir("DELIMITER")  # se esperaba un }
    self.funcion_actual = nombre_funcion[1]

    return NodoFuncion(tipo_retorno, nombre_funcion, parametros, cuerpo)

  def llamadafuncion(self):
    nombre = self.coincidir("IDENTIFIER")  # Nombre de la función
    self.coincidir("DELIMITER")  # se espera un parentesis (
    argumentos = []
    if not self.obtener_token_actual()[1] == ")":
      argumentos.append(self.coincidir("IDENTIFIER"))
      while self.obtener_token_actual()[1] == ",":
        self.coincidir("DELIMITER")
        argumentos.append(self.coincidir("IDENTIFIER"))
    self.coincidir("DELIMITER")

    namelist = []

    for funcion in self.funciones:
      namelist.append(funcion.nombre[1])

    if nombre[1] not in namelist:
      raise SyntaxError("No se declaro la función " + nombre[1] + ".")

    parametros = []
    for funcion in self.funciones:
      if funcion.nombre[1] == nombre[1]:
        parametros = funcion.parametros

    if len(argumentos) != len(parametros):
      raise SyntaxError("La cantidad de argumentos no coincide con la cantidad de parametros.")

    return NodoLlamadaFuncion(nombre, argumentos, parametros)

  def parametros(self):
    parametros = []
    # Reglas para parametros: int IDENTIFIER (, int IDENTIFIER)*
    tipo = self.coincidir("KEYWORD")  # Tipo del parametro
    nombre = self.coincidir("IDENTIFIER")  # Nombre del parametro
    parametros.append(NodoParametro(tipo, nombre))
    while self.obtener_token_actual() and self.obtener_token_actual()[1] == ",":
      self.coincidir("DELIMITER")  # se espera una ,
      tipo = self.coincidir("KEYWORD")  # Tipo del parametro
      nombre = self.coincidir("IDENTIFIER")  # Nombre del parametro
      parametros.append(NodoParametro(tipo, nombre))
      self.params.append(nombre[1])

    return parametros

  def cuerpo(self):

    instrucciones = []

    while self.obtener_token_actual() and self.obtener_token_actual()[1] != "}":
      if self.obtener_token_actual()[1] == "return":
        instrucciones.append(self.retorno())
      # El resto de instrucciones
      elif self.obtener_token_actual()[1] == "print":
        instrucciones.append(self.prints())

      elif self.obtener_token_actual()[1] == "if":
        instrucciones.append(self.ifs())

      elif self.obtener_token_actual()[1] == "while":
        instrucciones.append(self.whiles())

      elif self.obtener_token_actual()[1] == "for":
        instrucciones.append(self.fors())

      elif self.obtener_token_actual()[1] == "int" or self.obtener_token_actual()[1] == "float" or \
              self.obtener_token_actual()[1] == "string":
        instrucciones.append(self.asignacion(False))

      elif self.tokens[self.pos + 1][1] == "=" and self.obtener_token_actual():
        instrucciones.append(self.asignacion(True))

      elif self.obtener_token_actual()[0] == 'IDENTIFIER' and (self.tokens[self.pos + 1][1] == "++" or self.tokens[self.pos + 1][1] == "--"):
        instrucciones.append(self.actualizacion())

      elif self.obtener_token_actual()[0] == 'IDENTIFIER' and (self.tokens[self.pos + 1][1] == "+=" or self.tokens[self.pos + 1][1] == "-=" or self.tokens[self.pos + 1][1] == "*=" or self.tokens[self.pos + 1][1] == "/="):
        instrucciones.append(self.actualizacion2())

      else:
        raise SyntaxError(f'Expresión no válida: {self.obtener_token_actual()}')

    return instrucciones

  def asignacion(self, post):
    # Gramatica para una asignacion: IDENTIFIER OPERATOR IDENTIFIER
    global data_segment
    if not post:
      tipo = self.coincidir("KEYWORD")  # tipo
    nombre = self.coincidir("IDENTIFIER")  # Identificador <nombre de la variable>
    operador = self.coincidir("OPERATOR")  # operador ej. =
    if self.obtener_token_actual()[0] == "IDENTIFIER" and self.tokens[self.pos + 1][1] == "(":
      expresion = self.llamadafuncion()
    else:
      expresion = self.expresion()
    self.coincidir("DELIMITER")  # ;

    self.variables.append(nombre[1])

    return NodoAsignacion(nombre, expresion)

  def retorno(self):
    self.coincidir("KEYWORD")  # return
    expresion = self.expresion()
    self.coincidir("DELIMITER")  # ;

    return NodoRetorno(expresion)

  def expresion(self):
    izquierda = self.termino()
    while self.obtener_token_actual() and self.obtener_token_actual()[0] == "OPERATOR":
      operador = self.coincidir("OPERATOR")
      derecha = self.termino()
      izquierda = NodoOperacion(izquierda, operador, derecha)
    return izquierda

  def funciones_condicionales(self):
    self.coincidir("KEYWORD")
    if self.obtener_token_actual()[1] == "(":
      self.coincidir("DELIMITER")
    else:
      raise SyntaxError("Se esperaba un parentesis de condicional.")
    tokens = []
    while self.obtener_token_actual()[1] != "{":
      if self.tokens[self.pos + 1][1] == "{" and self.obtener_token_actual()[1] == ")":
        self.pos += 1
        break
      elif self.tokens[self.pos + 1][1] == "{" and self.obtener_token_actual()[1] != ")":
        raise SyntaxError("Debe cerrar el parentesis para las condiciones.")
      else:
        tokens.append(self.obtener_token_actual())
        self.pos += 1
    self.operaciones(tokens)
    self.cuerpo()
    self.coincidir("DELIMITER")

  def ifs(self):
    self.ifcounter[self.funcion_actual] = self.ifcounter.get(self.funcion_actual, 0) + 1
    self.coincidir("KEYWORD")
    elifs = []
    elses = None
    if self.obtener_token_actual()[1] == "(":
      self.coincidir("DELIMITER")
    else:
      raise SyntaxError("Se esperaba un parentesis de condicional.")
    condicional = self.expresion()
    self.coincidir("DELIMITER")
    self.coincidir("DELIMITER")
    cuerpo = self.cuerpo()
    self.coincidir("DELIMITER")

    while self.obtener_token_actual()[1] == "else" and self.tokens[self.pos + 1][1] == "if":
      self.coincidir("KEYWORD")
      self.coincidir("KEYWORD")
      self.coincidir("DELIMITER")
      condicionalelif = self.expresion()
      self.coincidir("DELIMITER")
      self.coincidir("DELIMITER")
      cuerpoelif = self.cuerpo()
      self.coincidir("DELIMITER")
      condicionalelif = NodoCondicion(condicionalelif.operador, condicionalelif.izquierda, condicionalelif.derecha)
      elifs.append(NodoElif(condicionalelif, cuerpoelif))

    if self.obtener_token_actual()[1] == "else":
      self.coincidir("KEYWORD")
      self.coincidir("DELIMITER")
      cuerpoelse = self.cuerpo()
      self.coincidir("DELIMITER")
      elses = NodoElse(cuerpoelse)

    condicional = NodoCondicion(condicional.operador, condicional.izquierda, condicional.derecha)

    return NodoIf(condicional, cuerpo, elifs, elses, self.funcion_actual, self.ifcounter[self.funcion_actual])

  def whiles(self):
    self.whilecounter[self.funcion_actual] = self.whilecounter.get(self.funcion_actual, 0) + 1
    self.coincidir("KEYWORD")
    if self.obtener_token_actual()[1] == "(":
      self.coincidir("DELIMITER")
    else:
      raise SyntaxError("Se esperaba un parentesis de condicional.")
    condicional = self.expresion()
    self.coincidir("DELIMITER")
    self.coincidir("DELIMITER")
    cuerpowhile = self.cuerpo()
    self.coincidir("DELIMITER")

    condicional = NodoCondicion(condicional.operador, condicional.izquierda, condicional.derecha)

    return NodoWhile(condicional, cuerpowhile, self.funcion_actual, self.whilecounter[self.funcion_actual])

  def fors(self):
    self.forcounter[self.funcion_actual] = self.forcounter.get(self.funcion_actual, 0) + 1
    self.coincidir("KEYWORD")
    self.coincidir("DELIMITER")
    self.coincidir("KEYWORD")
    inicializacion = self.asignacion(True)
    condicion = self.expresion()
    self.coincidir("DELIMITER")
    actualizacion = ""
    if self.obtener_token_actual()[0] == "IDENTIFIER" and \
            (self.tokens[self.pos + 1][1] == "++" or self.tokens[self.pos + 1][1] == "--"):
      actualizacion = NodoActualizacion(self.coincidir("IDENTIFIER")[1], self.coincidir("OPERATOR")[1])
      self.coincidir("DELIMITER")
    else:
      actualizacion = self.actualizacion2()

    self.coincidir("DELIMITER")
    cuerpofor = self.cuerpo()
    self.coincidir("DELIMITER")

    condicion = NodoCondicion(condicion.operador, condicion.izquierda, condicion.derecha)

    return NodoFor(inicializacion, condicion, actualizacion, cuerpofor, self.forcounter[self.funcion_actual], self.funcion_actual)

  def cadenas(self):
    words = ""
    self.coincidir("DELIMITER")
    while self.obtener_token_actual()[1] != '"':
      words += self.obtener_token_actual()[1] + " "
      self.pos += 1
    self.coincidir("DELIMITER")
    self.cad.append(words)
    return NodoCadena(words)

  def prints(self):
    self.coincidir("KEYWORD")
    self.coincidir("DELIMITER")
    if self.obtener_token_actual()[1] == '"':
      cadena = self.cadenas()
      self.coincidir("DELIMITER")
      self.coincidir("DELIMITER")
      return NodoPrint(cadena)
    else:
      exp = self.expresion();
      self.coincidir("DELIMITER");
      self.coincidir("DELIMITER");
      return NodoPrint(exp)

  def termino(self):
    token = self.obtener_token_actual()
    if token[0] == "NUMBER":
      return NodoNumero(self.coincidir("NUMBER"))
    elif token[0] == "IDENTIFIER":
      return NodoIdentificador(self.coincidir("IDENTIFIER"))
    else:
      raise SyntaxError(f'Expresión no válida: {token}')

  def actualizacion(self):
    val = NodoActualizacion(self.coincidir("IDENTIFIER")[1], self.coincidir("OPERATOR")[1])
    self.coincidir("DELIMITER")
    return val

  def actualizacion2(self):
    val = NodoActualizacion2(self.coincidir("IDENTIFIER")[1], self.coincidir("OPERATOR")[1], self.expresion())
    self.coincidir("DELIMITER")
    return val
  
  def input(self):
    self.coincidir("KEYWORD")
    self.coincidir("DELIMITER")
    if self.obtener_token_actual()[1] == '"':
      cadena = self.cadenas()
      self.coincidir("DELIMITER")
      self.coincidir("DELIMITER")
      return NodoInput(cadena)
    else:
      exp = self.expresion();
      self.coincidir("DELIMITER");
      self.coincidir("DELIMITER");
      return NodoInput(exp)


class NodoAST:
  # clase base oara todos los nodos del AST
  pass

  def traducir(self):
    raise NotImplementedError("Método traducir no implementado en este nodo")

  def generar_codigo(self):
    raise NotImplementedError("Método generar_codigo no implementado en este nodo")


class NodoProgram(NodoAST):
  # Nodo que representa el programa
  def __init__(self, funciones):
    self.funciones = funciones

  def traducir(self):
    return "\n".join(f.traducir() for f in self.funciones)

  def generar_codigo(self):
    codigo = ".code\n"

    for funcion in self.funciones:
      codigo += funcion.generar_codigo()

    codigo += "invoke ExitProcess, 0\nend main\n"
    return codigo


# se ejecuta en inicio proc far
class NodoLlamadaFuncion(NodoAST):
  # Nodo que representa una llamada a una función
  def __init__(self, nombre, argumentos, parametros):
    self.nombre = nombre
    self.argumentos = argumentos # los que se le mandan
    self.parametros = parametros # los que tiene la funcion

  def traducir(self):
    args = ",".join(a[1] for a in self.argumentos)
    return f"{self.nombre[1]}({args})"

  def generar_codigo(self):
    i = 0
    codigo = ""
    for parametro in self.parametros:
      if not(parametro.nombre[1] == self.argumentos[i][1]):
          codigo += f'           mov {parametro.nombre[1]}, {self.argumentos[i][1]} ;mover valor de parametro a su variable \n'
      i += 1
    codigo += f'           call {self.nombre[1]}\n'
    return codigo


class NodoFuncion(NodoAST):
  # Nodo que representa una función
  def __init__(self, tipo, nombre, parametros, cuerpo):
    self.tipo = tipo
    self.nombre = nombre
    self.parametros = parametros
    self.cuerpo = cuerpo

  def traducir(self):
    params = ",".join(p.traducir() for p in self.parametros)
    cuerpo = "\n    ".join(c.traducir() for c in self.cuerpo)
    return f"def {self.nombre[1]}({params}):\n    {cuerpo}"

  def generar_codigo(self):
    codigo = f"       {self.nombre[1]} proc\n"
    for inst in self.cuerpo:
      codigo += inst.generar_codigo()
    codigo += f"        {self.nombre[1]} endp\n"
    return codigo


class NodoParametro(NodoAST):
  # Nodo que representa un parámetro de una función
  def __init__(self, tipo, nombre):
    self.tipo = tipo
    self.nombre = nombre

  def traducir(self):
    return self.nombre[1]

  def generar_codigo(self):
    return f'{self.nombre[1]}'


class NodoAsignacion(NodoAST):
  # Nodo que representa una asignación de variable
  def __init__(self, nombre, expresion):
    self.nombre = nombre
    self.expresion = expresion

  def traducir(self):
    return f"{self.nombre[1]} = {self.expresion.traducir()}"

  def generar_codigo(self):
    if isinstance(self.expresion, NodoOperacion):
      self.expresion.optimizar()
    codigo = self.expresion.generar_codigo()
    codigo += f'\n           mov [{self.nombre[1]}], eax ;guardar en variable {self.nombre[1]}\n'
    return codigo


class NodoOperacion(NodoAST):
  # Nodo que representa una operación aritmética
  def __init__(self, izquierda, operador, derecha):
    self.izquierda = izquierda
    self.operador = operador
    self.derecha = derecha

  def traducir(self):
    return f"({self.izquierda.traducir()} {self.operador[1]} {self.derecha.traducir()})"

  def generar_codigo(self):
    codigo = []
    codigo.append(self.izquierda.generar_codigo())  # cargar el operando izquierdo
    codigo.append('           push eax; guardar en la pila\n')  # guardar el operando izq en la pila
    codigo.append(self.derecha.generar_codigo())  # cargar el operando derecho
    codigo.append('           pop ebx; recuperar de la pila\n')

    # ebx = opl y eax = op2
    if self.operador[1] == "+":
      codigo.append('           add eax, ebx; suma\n')
    elif self.operador[1] == "-":
      codigo.append('           sub ebx, eax; resta\n')
      codigo.append('           mov eax, ebx; guardar en eax\n')
    elif self.operador[1] == "*":
      codigo.append('           imul eax, ebx; multiplicacion\n')
    return '\n'.join(codigo)

  def optimizar(self):
    if isinstance(self.izquierda, NodoOperacion):
      self.izquierda = self.izquierda.optimizar()
    if isinstance(self.derecha, NodoOperacion):
      self.derecha = self.derecha.optimizar()

    if isinstance(self.izquierda, NodoIdentificador) or isinstance(self.derecha, NodoIdentificador):
        return self

    # Si ambos operandos son numeros, evaluamos la operacion
    if isinstance(self.izquierda, NodoNumero) and isinstance(self.derecha, NodoNumero):
      if self.operador[1] == "+":
        return NodoNumero(int(self.izquierda.valor[1]) + int(self.derecha.valor[1]))
      elif self.operador[1] == "-":
        return NodoNumero(int(self.izquierda.valor[1]) - int(self.derecha.valor[1]))
      elif self.operador[1] == "*":
        return NodoNumero(int(self.izquierda.valor[1]) * int(self.derecha.valor[1]))
      elif self.operador[1] == "/" and self.derecha.valor[1] != 0:
        return NodoNumero(int(self.izquierda.valor[1]) / int(self.derecha.valor[1]))



    # Simplificacion algebraica
    if self.operador[1] == "*" and isinstance(self.derecha, NodoNumero) and self.izquierda.valor == 0 or self.derecha.valor == 0:
      return NodoNumero(0)
    if self.operador[1] == "*" and isinstance(self.derecha, NodoNumero) and self.izquierda.valor == 1:
      return self.derecha
    if self.operador[1] == "*" and isinstance(self.derecha, NodoNumero) and self.derecha.valor == 1:
      return self.izquierda
    if self.operador[1] == "+" and isinstance(self.derecha, NodoNumero) and self.izquierda.valor == 0:
      return self.derecha
    if self.operador[1] == "+" and isinstance(self.derecha, NodoNumero) and self.derecha.valor == 0:
      return self.izquierda
    if self.operador[1] == "-" and isinstance(self.derecha, NodoNumero) and self.izquierda.valor == 0:
      return NodoNumero(0)
    if self.operador[1] == "-" and isinstance(self.derecha, NodoNumero) and self.derecha.valor == 0:
      return self.izquierda
    if self.operador[1] == "/" and isinstance(self.derecha, NodoNumero) and self.derecha.valor == 1:
      return self.izquierda
    if self.operador[1] == "/" and isinstance(self.derecha, NodoNumero) and self.izquierda.valor == 0:
      return NodoNumero(0)

    return NodoOperacion(self.izquierda, self.operador, self.derecha)


class NodoRetorno(NodoAST):
  # Nodo que representa a la sentencia return
  def __init__(self, expresion):
    self.expresion = expresion

  def traducir(self):
    return f"return {self.expresion.traducir()}"

  def generar_codigo(self):
    if isinstance(self.expresion, NodoOperacion):
      self.expresion.optimizar()
    elif isinstance(self.expresion, NodoIdentificador):
      return f'           mov eax, [{self.expresion.nombre[1]}] ;cargar variable {self.expresion.nombre[1]} en eax\n           ret\n'
    elif isinstance(self.expresion, NodoNumero):
      return f'           mov eax, {self.expresion.valor[1]} ;cargar numero {self.expresion.valor[1]} en ax\n           ret\n'
    return self.expresion.generar_codigo() + '\n           ret\n'


class NodoIdentificador(NodoAST):
  # Nodo que representa un identificador
  def __init__(self, nombre):
    self.nombre = nombre

  def traducir(self):
    return self.nombre[1]

  def generar_codigo(self):
    return f'           mov eax, [{self.nombre[1]}] ;cargar variable {self.nombre[1]} en eax\n'


class NodoNumero(NodoAST):
  # Nodo que representa un número
  def __init__(self, valor):
    self.valor = valor

  def traducir(self):
    return str(self.valor[1])

  def generar_codigo(self):
    return f'           mov eax, {self.valor[1]} ;cargar numero {self.valor[1]} en ax\n'


class NodoCadena(NodoAST):
  # Nodo que representa una cadena
  def __init__(self, palabras):
    self.palabras = palabras

  def traducir(self):
    return self.palabras

  def generar_codigo(self):
    return f"'{self.palabras}'\n"


class NodoPrint(NodoAST):
  # Nodo que representa una sentencia print
  def __init__(self, expresion):
    self.expresion = expresion

  def traducir(self):
    return f"print({self.expresion.traducir()})"

  def generar_codigo(self):
    codigo = ""
    if isinstance(self.expresion, NodoCadena):
      codigo += f'           invoke StdOut, offset {self.expresion.palabras.replace(" ", "")} \n'
      codigo += f"           add esp, 8\n"
    else:
      if isinstance(self.expresion, NodoOperacion):
        self.expresion.optimizar()
      codigo = self.expresion.generar_codigo()
      codigo += f'           invoke dwtoa, eax, offset buffer\n'
      codigo += f'           invoke StdOut, offset buffer\n'
      codigo += f'           invoke StdOut, offset saltoLinea\n'
      codigo += f'           add esp, 8\n'
      codigo += f'           mov eax, 0\n'
    return codigo


class NodoCondicion(NodoAST):
  # Nodo que representa una condición
  def __init__(self, operador, izquierda, derecha):
    self.operador = operador
    self.izquierda = izquierda
    self.derecha = derecha

  def generar_codigo(self):
    codigo = ""
    if isinstance(self.izquierda, NodoNumero):
      codigo += f'           mov eax, {self.izquierda.valor[1]}\n' #izq
    if isinstance(self.derecha, NodoNumero):
      codigo += f'           mov ebx, {self.derecha.valor[1]}\n' #der
    if isinstance(self.izquierda, NodoIdentificador):
      codigo += f'           mov eax, [{self.izquierda.nombre[1]}]\n' #izq
    if isinstance(self.derecha, NodoIdentificador):
      codigo += f'           mov ebx, [{self.derecha.nombre[1]}]\n' #der
    return codigo

  def traducir(self):
    return ""


class NodoIf(NodoAST):
  # Nodo que representa una sentencia if
  def __init__(self, condicion, cuerpo, elseif, elses, nombre_funcion, id):
    self.nombre_funcion = nombre_funcion
    self.id = id
    self.condicion = condicion
    self.cuerpo = cuerpo
    self.elseif = elseif # []
    self.elses = elses # nodoelse

  def traducir(self):
    pass

  def generar_codigo(self):
    endif = f'{self.nombre_funcion}if{self.id}_end\n'
    i = 0
    codigo = ""
    codigo += self.condicion.generar_codigo()
    codigo += '           cmp eax, ebx; comparar\n'
    next = self.get_nextInst(i)
    tr_label = self.get_lbl('if')
    codigo += self.jump(tr_label, next, self.condicion.operador[1])
    codigo += tr_label
    codigo += self.body(self.cuerpo)
    codigo += f'           jmp {endif}'
    while i < len(self.elseif):
      print('i', i)
      cond = self.elseif[i].condicion
      codigo += self.get_lbl(f'elif{i + 1}')
      codigo += cond.generar_codigo()
      codigo += '           cmp eax, ebx; comparar\n'
      next = self.get_nextInst(i + 1)
      codigo += self.jump("", next, cond.operador[1])
      codigo += self.body(self.elseif[i].cuerpo)
      codigo += f'           jmp {endif}'
      i += 1


    if self.elses != None:
      codigo += self.get_lbl(f'else{self.id}')
      codigo += self.body(self.elses.cuerpo)

    codigo += f'           {self.nombre_funcion}if{self.id}_end:\n'
    return codigo

  def body(self, body):
    code = ""
    for inst in body:
      code += inst.generar_codigo()
    return code

  def get_nextInst(self, k):
    print('k', k + 1)
    if len(self.elseif) + 1 > k + 1 and self.elseif != []:
        return self.get_lbl(f'elif{k + 1}')
    if self.elses != None:
      return self.get_lbl(f'else{self.id}')
    return f'{self.nombre_funcion}if{self.id}_end'

  def get_lbl(self, ty):
    return f'           {self.nombre_funcion}if{self.id}_bl{ty}:\n'

  def jump(self, lbl_tr, lbl_fl, op):
    cnd = ""
    tr = lbl_tr.replace(":", "").replace("           ", "")
    fl = lbl_fl.replace(":", "").replace("           ", "")
    if op == "==":
      cnd += f'             je {tr}' if lbl_tr != "" else ""
      cnd += f'             jne {fl}'
    elif op == "!=":
      cnd += f'             jne {tr}' if lbl_tr != "" else ""
      cnd += f'             je {fl}'
    elif op == "<":
      cnd += f'             jl {tr}' if lbl_tr != "" else ""
      cnd += f'             jge {fl}'
    elif op == "<=":
      cnd += f'             jle {tr}' if lbl_tr != "" else ""
      cnd += f'             jg {fl}'
    elif op == ">":
      cnd += f'             jg {tr}' if lbl_tr != "" else ""
      cnd += f'             jle {fl}'
    elif op == ">=":
      cnd += f'             jge {tr}' if lbl_tr != "" else ""
      cnd += f'             jl {fl}'
    return cnd


class NodoElif(NodoAST):
  # Nodo que representa una sentencia elif
  def __init__(self, condicion, cuerpo):
    self.condicion = condicion
    self.cuerpo = cuerpo

  def traducir(self):
    return f"elif {self.condicion.traducir()}:\n    {self.cuerpo.traducir()}"

  def generar_codigo(self):
    codigo = self.condicion.generar_codigo()
    codigo += self.cuerpo.generar_codigo()
    return codigo


class NodoElse(NodoAST):
  # Nodo que representa una sentencia else
  def __init__(self, cuerpo):
    self.cuerpo = cuerpo

  def traducir(self):
    return f"else:\n    {self.cuerpo.traducir()}"


class NodoWhile(NodoAST):
  # Nodo que representa una sentencia while
  def __init__(self, condicion, cuerpo, function, id):
    self.funcion = function
    self.id = id
    self.condicion = condicion
    self.cuerpo = cuerpo

  def traducir(self):
    return f"while {self.condicion.traducir()}:\n    {self.cuerpo.traducir()}"

  def generar_codigo(self):
    label = f'{self.funcion}_while_{self.id}'
    endwhile = f'{self.funcion}_endwhile_{self.id}'
    codigo = self.condicion.generar_codigo()
    codigo += '           cmp eax, ebx; comparar\n'
    codigo += self.jump("", endwhile, self.condicion.operador[1])
    codigo += "           " + label + ":\n"
    codigo += self.body(self.cuerpo)
    codigo += self.condicion.generar_codigo()
    codigo += '           cmp eax, ebx; comparar\n'
    codigo += self.jump(label, endwhile, self.condicion.operador[1])
    codigo += f'           {endwhile}:\n'

    return codigo

  def body(self, body):
    code = ""
    for inst in body:
      code += inst.generar_codigo()
    return code

  def jump(self, lbl_tr, lbl_fl, op):
    cnd = ""
    if op == "==":
      cnd += f'             je {lbl_tr}\n' if lbl_tr != "" else ""
      cnd += f'             jne {lbl_fl}\n'
    elif op == "!=":
      cnd += f'             jne {lbl_tr}\n' if lbl_tr != "" else ""
      cnd += f'             je {lbl_fl}\n'
    elif op == "<":
      cnd += f'             jl {lbl_tr}\n' if lbl_tr != "" else ""
      cnd += f'             jge {lbl_fl}\n'
    elif op == "<=":
      cnd += f'             jle {lbl_tr}\n' if lbl_tr != "" else ""
      cnd += f'             jg {lbl_fl}\n'
    elif op == ">":
      cnd += f'             jg {lbl_tr}\n' if lbl_tr != "" else ""
      cnd += f'             jle {lbl_fl}\n'
    elif op == ">=":
      cnd += f'             jge {lbl_tr}\n' if lbl_tr != "" else ""
      cnd += f'             jl {lbl_fl}\n'
    return cnd


class NodoFor(NodoAST):
  # Nodo que representa una sentencia for
  def __init__(self, inicializacion, condicion, actualizacion, cuerpo, id, funcion):
    self.inicializacion = inicializacion
    self.condicion = condicion
    self.actualizacion = actualizacion
    self.cuerpo = cuerpo
    self.id = id
    self.funcion = funcion


  def traducir(self):
    return f"for {self.inicializacion.traducir()} {self.condicion.traducir()} {self.actualizacion.traducir()}:\n    {self.cuerpo.traducir()}"

  def generar_codigo(self):
    endfor = f'{self.funcion}_endfor_{self.id}'
    label = f'{self.funcion}_for_{self.id}'
    codigo = self.inicializacion.generar_codigo()
    codigo += self.condicion.generar_codigo()
    codigo += '           cmp eax, ebx; comparar\n'
    codigo += self.jump("", endfor, self.condicion.operador[1])
    codigo += "           " + label + ":\n"
    codigo += self.body(self.cuerpo)
    codigo += self.actualizacion.generar_codigo()
    codigo += self.condicion.generar_codigo()
    codigo += '           cmp eax, ebx; comparar\n'
    codigo += self.jump(label, endfor, self.condicion.operador[1])
    codigo += f'           {endfor}:\n'
    return codigo

  def jump(self, lbl_tr, lbl_fl, op):
    cnd = ""
    if op == "==":
      cnd += f'             je {lbl_tr}\n' if lbl_tr != "" else ""
      cnd += f'             jne {lbl_fl}\n'
    elif op == "!=":
      cnd += f'             jne {lbl_tr}\n' if lbl_tr != "" else ""
      cnd += f'             je {lbl_fl}\n'
    elif op == "<":
      cnd += f'             jl {lbl_tr}\n' if lbl_tr != "" else ""
      cnd += f'             jge {lbl_fl}\n'
    elif op == "<=":
      cnd += f'             jle {lbl_tr}\n' if lbl_tr != "" else ""
      cnd += f'             jg {lbl_fl}\n'
    elif op == ">":
      cnd += f'             jg {lbl_tr}\n' if lbl_tr != "" else ""
      cnd += f'             jle {lbl_fl}\n'
    elif op == ">=":
      cnd += f'             jge {lbl_tr}\n' if lbl_tr != "" else ""
      cnd += f'             jl {lbl_fl}\n'
    return cnd

  def body(self, body):
    code = ""
    for inst in body:
      code += inst.generar_codigo()
    return code



class NodoActualizacion(NodoAST):
  def __init__(self, nombre, operador):
    self.nombre = nombre
    self.operador = operador

  def traducir(self):
    return f"{self.nombre[1]} {self.operador[1]}"

  def generar_codigo(self):
    if self.operador == "++":
      return f'           inc {self.nombre}\n'
    elif self.operador == "--":
      return f'           dec {self.nombre}\n'
    return ""

class NodoActualizacion2(NodoAST):
  def __init__(self, nombre, operador, valor):
    self.nombre = nombre
    self.operador = operador
    self.valor = valor

  def traducir(self):
    return f"{self.nombre[1]} {self.operador[1]} {self.valor[1]}"

  def generar_codigo(self):
    codigo = ""
    res = None
    if isinstance(self.valor, NodoNumero):
      res = self.valor
    elif isinstance(self.valor, NodoIdentificador):
      res = self.valor.nombre
      codigo += f'           mov eax, [{res[1]}]\n'
    elif isinstance(self.valor, NodoOperacion):
      res = self.valor.optimizar()
      if isinstance(res, NodoNumero):
        codigo += f'           mov eax, {res.valor}\n'
      elif isinstance(res, NodoIdentificador):
        codigo += f'           mov eax, [{res.nombre[1]}]\n'
      else:
        codigo += self.valor.generar_codigo()
    if self.operador == "+=":
      codigo += f'           add {self.nombre}, eax\n'
    elif self.operador == "-=":
      codigo += f'           sub {self.nombre}, eax\n'
    elif self.operador == "*=":
      codigo += f'           imul {self.nombre}, eax\n'
    elif self.operador == "/=":
      codigo += f'           idiv eax\n'
    return codigo
  
class NodoInput(NodoAST):
  # Nodo que representa una entrada de datos
  def __init__(self, nombre):
      self.nombre = nombre

  def traducir(self):
      return f"{self.nombre[1]} = input()"

  def generar_codigo(self):
      return f'           invoke StdIn, offset {self.nombre[1]}\n'


import json

codigo_fuente = """
int main() {
    int i = 1;
    int suma = 0;

    while (i <= 5) {
        suma += i;
        i++;
    }
    print(suma);

    print("Numeros del 1 al 5 usando for:");
    for (int j = 1; j <= 5; j++) {
        print(j);
    }

    if (suma > 10) {
        print("La suma es mayor que 10.");
    } else if (suma == 10) {
        print("La suma es igual a 10.");
    } else {
        print("La suma es menor que 10.");
    }
}

"""

tokens = identificar_tokens(codigo_fuente)
print("Tokens encontrados:")
i = 0
for token in tokens:
  print(f'{i} {token}')
  i += 1

parser = None
try:
  print("\Iniciando análisis sintáctico...")
  parser = Parser(tokens)
  arbol_ast = parser.parsear()
  print("Análisis sintáctico correcto.")
except SyntaxError as e:
  print(f"Error Sintáctico: {e}")

p = parser.params
variables = parser.variables
data = """
.386
.model flat, stdcall
.stack 4096
option casemap :none

include \masm32\include\masm32.inc
include \masm32\include\kernel32.inc
includelib \masm32\lib\masm32.lib
includelib \masm32\lib\kernel32.lib

.data
    format db "%d", 10, 0
    buffer db 12 dup(0)
    saltoLinea db 13, 10, 0
    ;seccion cadenas
"""

for cadena in parser.cad:
  data += "         " + cadena.replace(" ", "") + " db '" + cadena + "', 13, 10, 0\n"

data += "         ;seccion de variables\n"

for var in variables:
  data += "         " + var + " dd 0\n"

data += "         ;seccion de parametros\n"

for param in p:
  if param not in variables:
    data += "         " + param + " dd 0\n"

def imprimir_ast(nodo):
  if isinstance(nodo, NodoProgram):
    return {'Program': [imprimir_ast(f) for f in nodo.funciones]}
  elif isinstance(nodo, NodoFuncion):
    return {'Funcion': nodo.nombre,
            'Parametros': [imprimir_ast(p) for p in nodo.parametros],
            'Cuerpo': [imprimir_ast(c) for c in nodo.cuerpo]}
  elif isinstance(nodo, NodoParametro):
    return {'Parametro': nodo.nombre,
            'Tipo': nodo.tipo}
  elif isinstance(nodo, NodoAsignacion):
    return {'Asignacion': nodo.nombre,
            'Expresion': imprimir_ast(nodo.expresion)}
  elif isinstance(nodo, NodoOperacion):
    return {'Operacion': nodo.operador,
            'Izquierda': imprimir_ast(nodo.izquierda),
            'Derecha': imprimir_ast(nodo.derecha)}
  elif isinstance(nodo, NodoRetorno):
    return {'Retorno': imprimir_ast(nodo.expresion)}
  elif isinstance(nodo, NodoIdentificador):
    return {'Identificador': nodo.nombre}
  elif isinstance(nodo, NodoNumero):
    return {'Numero': nodo.valor}
  elif isinstance(nodo, NodoCadena):
    return {'Cadena': nodo.palabras}
  elif isinstance(nodo, NodoPrint):
    return {'Print': imprimir_ast(nodo.expresion)}
  elif isinstance(nodo, NodoIf):
    return {'If': imprimir_ast(nodo.condicion),
            'Cuerpo': [imprimir_ast(c) for c in nodo.cuerpo],
            'Elseif': [imprimir_ast(e) for e in nodo.elseif],
            'Else': imprimir_ast(nodo.elses)}
  elif isinstance(nodo, NodoElif):
    return {'Elif': imprimir_ast(nodo.condicion),
            'Cuerpo': [imprimir_ast(c) for c in nodo.cuerpo]}
  elif isinstance(nodo, NodoElse):
    return {'Else': [imprimir_ast(c) for c in nodo.cuerpo]}
  elif isinstance(nodo, NodoWhile):
    return {'While': imprimir_ast(nodo.condicion),
            'Cuerpo': [imprimir_ast(c) for c in nodo.cuerpo]}
  elif isinstance(nodo, NodoFor):
    return {'For': imprimir_ast(nodo.inicializacion),
            'Condicion': imprimir_ast(nodo.condicion),
            'Actualizacion': imprimir_ast(nodo.actualizacion),
            'Cuerpo': [imprimir_ast(c) for c in nodo.cuerpo]}
  elif isinstance(nodo, NodoActualizacion):
    return {'Actualizacion': nodo.nombre,
            'Operador': nodo.operador}

  elif isinstance(nodo, NodoActualizacion2):
    return {'Actualizacion': nodo.nombre,
            'Operador': nodo.operador,
            'Valor': imprimir_ast(nodo.valor)}
  # return {}


print(json.dumps(imprimir_ast(arbol_ast), indent=1))

codigo_assembler = data + arbol_ast.generar_codigo()
print(codigo_assembler)

name = input("Ingrese el nombre del archivo .asm: ")
root = f'C:\\masm32\\projects\\{name}.asm'

with open(root, "w", encoding="utf-8") as archivo:
    archivo.write(codigo_assembler)

print(f"Archivo ensamblador guardado en: {root}")

print("Comandos: ")
print(f'\\masm32\\bin\ml /c /coff /I"C:\\masm32\\include" projects/{name}.asm')
print(f'C:\\masm32\\bin\\link.exe /subsystem:console {name}.obj')
print(f'{name}.exe')







