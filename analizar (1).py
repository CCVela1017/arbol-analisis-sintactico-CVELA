import re

token_patron = {
    "KEYWORD": r'\b(if|else|for|while|print|return|int|float|void)\b',
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
        funciones = []
        while self.obtener_token_actual():
            if self.obtener_token_actual()[1] == "int" or self.obtener_token_actual()[1] == "float" \
                    or self.obtener_token_actual()[1] == "string" or self.obtener_token_actual()[1] == "void":
                funciones.append(self.funcion())

        namelist = []

        for funcion in funciones:
            namelist.append(funcion.nombre[1])

        if "main" not in namelist:
            raise SyntaxError("No se encontró la función main.")

        return NodoProgram(funciones);

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
        cuerpo = self.cuerpo()
        self.coincidir("DELIMITER")  # se esperaba un }

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
        return NodoLlamadaFuncion(nombre, argumentos)

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

        return parametros

    def cuerpo(self):

        instrucciones = []

        while self.obtener_token_actual() and self.obtener_token_actual()[1] != "}":
            if self.obtener_token_actual()[1] == "return":
                instrucciones.append(self.retorno())
            else:
                # El resto de instrucciones
                if self.obtener_token_actual()[1] == "print":
                    instrucciones.append(self.prints())

                if self.obtener_token_actual()[1] == "if":
                    instrucciones.append(self.ifs())

                if self.obtener_token_actual()[1] == "while":
                    instrucciones.append(self.whiles())

                if self.obtener_token_actual()[1] == "for":
                    instrucciones.append(self.fors())

                if self.obtener_token_actual()[1] == "int" or self.obtener_token_actual()[1] == "float" or \
                        self.obtener_token_actual()[1] == "string":
                    instrucciones.append(self.asignacion(False))

                if self.tokens[self.pos + 1][1] == "=" and self.obtener_token_actual():
                    instrucciones.append(self.asignacion(True))

        return instrucciones

    def asignacion(self, post):
        # Gramatica para una asignacion: IDENTIFIER OPERATOR IDENTIFIER
        if not post:
            tipo = self.coincidir("KEYWORD")  # tipo
        nombre = self.coincidir("IDENTIFIER")  # Identificador <nombre de la variable>
        operador = self.coincidir("OPERATOR")  # operador ej. =
        if self.obtener_token_actual()[0] == "IDENTIFIER" and self.tokens[self.pos + 1][1] == "(":
            expresion = self.llamadafuncion()
        else:
            expresion = self.expresion()
        self.coincidir("DELIMITER")  # ;

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
        elifs = []
        elses = None
        self.coincidir("KEYWORD")
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
            elifs.append(NodoElif(condicionalelif, cuerpoelif))

        if self.obtener_token_actual()[1] == "else":
            self.coincidir("KEYWORD")
            self.coincidir("DELIMITER")
            cuerpoelse = self.cuerpo()
            self.coincidir("DELIMITER")
            elses = NodoElse(cuerpoelse)

        return NodoIf(condicional, cuerpo, elifs, elses)

    def whiles(self):
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

        return NodoWhile(condicional, cuerpowhile)

    def fors(self):
        self.coincidir("KEYWORD")
        self.coincidir("DELIMITER")
        self.coincidir("KEYWORD")
        inicializacion = self.expresion()
        self.coincidir("DELIMITER")
        condicion = self.expresion()
        self.coincidir("DELIMITER")
        actualizacion = ""
        if self.obtener_token_actual()[0] == "IDENTIFIER" and \
                (self.tokens[self.pos + 1][1] == "++" or self.tokens[self.pos + 1][1] == "--"):
            actualizacion = NodoActualizacion(self.coincidir("IDENTIFIER")[1], self.coincidir("OPERATOR")[1])
        else:
            actualizacion = self.expresion()
        self.coincidir("DELIMITER")

        self.coincidir("DELIMITER")
        cuerpofor = self.cuerpo()
        self.coincidir("DELIMITER")

        return NodoFor(inicializacion, condicion, actualizacion, cuerpofor)

    def cadenas(self):
        words = ""
        self.coincidir("DELIMITER")
        while self.obtener_token_actual()[1] != '"':
            words += self.obtener_token_actual()[1] + " "
            self.pos += 1
        self.coincidir("DELIMITER")
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


class NodoAST:
    # clase base oara todos los nodos del AST
    pass


class NodoProgram(NodoAST):
    # Nodo que representa el programa
    def __init__(self, funciones):
        self.funciones = funciones


class NodoLlamadaFuncion(NodoAST):
    # Nodo que representa una llamada a una función
    def __init__(self, nombre, argumentos):
        self.nombre = nombre
        self.argumentos = argumentos


class NodoFuncion(NodoAST):
    # Nodo que representa una función
    def __init__(self, tipo, nombre, parametros, cuerpo):
        self.tipo = tipo
        self.nombre = nombre
        self.parametros = parametros
        self.cuerpo = cuerpo


class NodoParametro(NodoAST):
    # Nodo que representa un parámetro de una función
    def __init__(self, tipo, nombre):
        self.tipo = tipo
        self.nombre = nombre


class NodoAsignacion(NodoAST):
    # Nodo que representa una asignación de variable
    def __init__(self, nombre, expresion):
        self.nombre = nombre
        self.expresion = expresion


class NodoOperacion(NodoAST):
    # Nodo que representa una operación aritmética
    def __init__(self, izquierda, operador, derecha):
        self.izquierda = izquierda
        self.operador = operador
        self.derecha = derecha


class NodoRetorno(NodoAST):
    # Nodo que representa a la sentencia return
    def __init__(self, expresion):
        self.expresion = expresion


class NodoIdentificador(NodoAST):
    # Nodo que representa un identificador
    def __init__(self, nombre):
        self.nombre = nombre


class NodoNumero(NodoAST):
    # Nodo que representa un número
    def __init__(self, valor):
        self.valor = valor


class NodoCadena(NodoAST):
    # Nodo que representa una cadena
    def __init__(self, palabras):
        self.palabras = palabras


class NodoPrint(NodoAST):
    # Nodo que representa una sentencia print
    def __init__(self, expresion):
        self.expresion = expresion


class NodoIf(NodoAST):
    # Nodo que representa una sentencia if
    def __init__(self, condicion, cuerpo, elseif, elses):
        self.condicion = condicion
        self.cuerpo = cuerpo
        self.elseif = elseif
        self.elses = elses


class NodoElif(NodoAST):
    # Nodo que representa una sentencia elif
    def __init__(self, condicion, cuerpo):
        self.condicion = condicion
        self.cuerpo = cuerpo


class NodoElse(NodoAST):
    # Nodo que representa una sentencia else
    def __init__(self, cuerpo):
        self.cuerpo = cuerpo


class NodoWhile(NodoAST):
    # Nodo que representa una sentencia while
    def __init__(self, condicion, cuerpo):
        self.condicion = condicion
        self.cuerpo = cuerpo


class NodoFor(NodoAST):
    # Nodo que representa una sentencia for
    def __init__(self, inicializacion, condicion, actualizacion, cuerpo):
        self.inicializacion = inicializacion
        self.condicion = condicion
        self.actualizacion = actualizacion
        self.cuerpo = cuerpo


class NodoActualizacion(NodoAST):
    def __init__(self, nombre, operador):
        self.nombre = nombre
        self.operador = operador


import json

codigo_fuente = """
int suma(int a, int b) {
  int c = a + b;
  print("La suma de a y b es: ");
  if (c > 10) {
    print(c);
  } else if (c < 10) {
    print(c);
  } else {
    print(c);
  }
  while (c > 10) {
    c = c - 1;
  }
  for (int i = 0; i < 10; i++) {
    c = c + 1;
  }
  return c;
}

int main() {
  int a = 5;
  int b = 10;
  int c = suma(a, b);
  print(c);
  return 0;
}
"""

tokens = identificar_tokens(codigo_fuente)
print("Tokens encontrados:")
i = 0
for token in tokens:
    print(f'{i} {token}')
    i += 1

try:
    print("\Iniciando análisis sintáctico...")
    parser = Parser(tokens)
    arbol_ast = parser.parsear()
    print("Análisis sintáctico correcto.")
except SyntaxError as e:
    print(f"Error Sintáctico: {e}")


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
    # return {}


print(json.dumps(imprimir_ast(arbol_ast), indent=1))
