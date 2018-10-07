from OpenGL.GL import *

vertshader = """
#version 330
layout(location = 0) in vec4 vert;
layout(location = 2) in vec2 texCoord;


out vec2 fragTexCoord;

void main(void)
{
    // Pass the tex coord straight through to the fragment shader
    fragTexCoord = texCoord;
    //vec4 a = vec4(vert, 1.0);
    vec4 a = vert;
    //a.x = a.x * 0.5;
    //a.y = a.y * 0.5;


   gl_Position = gl_ModelViewProjectionMatrix * a;
}   
"""

fragshader = """
#version 330
in vec2 fragTexCoord; //this is the texture coord
out vec4 finalColor; //this is the output color of the pixel
uniform sampler2D tex;

void main (void)
{
    //finalColor = vec4(1.0, 1.0, 0.0, 1.0);
    //finalColor = vec4(fragTexCoord, 1.0, 1.0);
    //finalColor = texture(tex, fragTexCoord);
    vec4 color = texture(tex, fragTexCoord);
    if (color.a < 0.5) {
        discard;
    }
    finalColor = color;
}
"""

def _compile_shader_with_error_report(shaderobj):
    glCompileShader(shaderobj)
    if not glGetShaderiv(shaderobj, GL_COMPILE_STATUS):
        raise RuntimeError(str(glGetShaderInfoLog(shaderobj), encoding="ascii"))

def create_shader():
    #print(glGetString(GL_VENDOR))
    vertexShaderObject = glCreateShader(GL_VERTEX_SHADER)
    fragmentShaderObject = glCreateShader(GL_FRAGMENT_SHADER)
    #glShaderSource(vertexShaderObject, 1, vertshader, len(vertshader))
    #glShaderSource(fragmentShaderObject, 1, fragshader, len(fragshader))
    glShaderSource(vertexShaderObject, vertshader)
    glShaderSource(fragmentShaderObject, fragshader)

    _compile_shader_with_error_report(vertexShaderObject)
    _compile_shader_with_error_report(fragmentShaderObject)
    
    program = glCreateProgram()

    glAttachShader(program, vertexShaderObject)
    glAttachShader(program, fragmentShaderObject)

    glLinkProgram(program)

    return program