from OpenGL.GL import *

vertshader = """
#version 330 compatibility
layout(location = 0) in vec4 vert;
layout(location = 2) in vec2 texCoord;
layout(location = 3) in vec3 normal;
layout(location = 4) in vec2 bumpCoord;
layout(location = 5) in vec3 binormal;
layout(location = 6) in vec3 tangent;

out vec2 fragTexCoord;
out vec3 vecNormal;
out vec3 vecBinormal;
out vec3 vecTangent;
out vec2 bumpTexCoord;

uniform mat4 modelview;

mat4 scale = mat4(
-1.0, 0.0, 0.0, 0.0,
0.0, 1.0, 0.0, 0.0,
0.0, 0.0, 1.0, 0.0,
0.0, 0.0, 0.0, 1.0);

void main(void)
{
    // Pass the tex coord straight through to the fragment shader
    fragTexCoord = texCoord;
    bumpTexCoord = bumpCoord;
    //fragmodelview = modelview;
    mat4 nrmmat = inverse(transpose(modelview));
    vecNormal = vec3(nrmmat*vec4(normal, 0.0));//vec3(gl_ModelViewProjectionMatrix*vec4(normal, 0.0));
    vecBinormal = vec3(nrmmat*vec4(binormal, 0.0));
    vecTangent = vec3(nrmmat*vec4(tangent, 0.0));
    //vecNormal = normal;
    //vecBinormal = binormal;
    //vecTangent = tangent;
    
    //vec4 a = vec4(vert, 1.0);
    vec4 a = vert;
    //a.x = a.x * 0.5;
    //a.y = a.y * 0.5;


   gl_Position = gl_ModelViewProjectionMatrix* a;
}   
"""

vertshaderSimple = """
#version 330 compatibility
layout(location = 0) in vec4 vert;
layout(location = 2) in vec2 texCoord;
layout(location = 3) in vec3 normal;
layout(location = 4) in vec2 bumpCoord;
layout(location = 5) in vec3 binormal;
layout(location = 6) in vec3 tangent;

out vec2 fragTexCoord;
out vec3 vecNormal;
out vec3 vecBinormal;
out vec3 vecTangent;
out vec2 bumpTexCoord;

uniform mat4 modelview;

mat4 scale = mat4(
-1.0, 0.0, 0.0, 0.0,
0.0, 1.0, 0.0, 0.0,
0.0, 0.0, 1.0, 0.0,
0.0, 0.0, 0.0, 1.0);

void main(void)
{
    // Pass the tex coord straight through to the fragment shader
    fragTexCoord = texCoord;
    bumpTexCoord = bumpCoord;
    //fragmodelview = modelview;
    mat4 nrmmat = inverse(transpose(modelview));
    vecNormal = vec3(nrmmat*vec4(normal, 0.0));//vec3(gl_ModelViewProjectionMatrix*vec4(normal, 0.0));
    vecBinormal = vec3(nrmmat*vec4(binormal, 0.0));
    vecTangent = vec3(nrmmat*vec4(tangent, 0.0));
    //vecNormal = normal;
    //vecBinormal = binormal;
    //vecTangent = tangent;

    //vec4 a = vec4(vert, 1.0);
    vec4 a = vert;
    //a.x = a.x * 0.5;
    //a.y = a.y * 0.5;


   gl_Position = gl_ModelViewProjectionMatrix* a;
}   
"""
fragshader = """
#version 330
in vec2 fragTexCoord; //this is the texture coord
in vec3 vecNormal; // normal vector
in vec3 vecBinormal;
in vec3 vecTangent;
in vec2 bumpTexCoord; // coordinates on bump texture

out vec4 finalColor; //this is the output color of the pixel
uniform sampler2D tex;
uniform sampler2D bump;

uniform vec3 light;// = vec3(0.0, 1.0, 0.0);
vec4 ambient = vec4(0.1, 0.1, 0.1, 1.0);

void clampvector(in vec4 vector, out vec4 result) {
    result.x = clamp(vector.x, 0.0, 1.0);
    result.y = clamp(vector.y, 0.0, 1.0);
    result.z = clamp(vector.z, 0.0, 1.0);
    result.w = clamp(vector.w, 0.0, 1.0);
}

void main (void)
{
    //finalColor = vec4(1.0, 1.0, 0.0, 1.0);
    //vec4 color = vec4(fragTexCoord, 1.0, 1.0);
    //finalColor = texture(tex, fragTexCoord);
    vec4 color = texture(tex, fragTexCoord);
    
    if (color.a == 0.0) {
        discard;
    }
    
    vec4 bumpvec = texture(bump, bumpTexCoord);
    float offset_tangent = (bumpvec.a-0.5)*2;
    float offset_binormal = (bumpvec.r-0.5)*2;
    
    vec3 finalVecNormal = vecNormal + offset_binormal*vecBinormal + offset_tangent*vecTangent;
    finalVecNormal = normalize(finalVecNormal);
    vec3 normlight = normalize(light);
    
    //float angle = dot(light, vecNormal) * inversesqrt(length(light)) * inversesqrt(length(vecNormal));
    float angle = dot(normlight, finalVecNormal);
    if (length(vecNormal) == 0.0) {
        angle = -1.0;
    }
    angle = clamp((-1*angle+1)/2.0, 0.2, 1.0);
    //float angle = 1.0;
    //finalColor = color*angle;
    //vec4 lightcolor = vec4(1.0, 0.0, 0.0, 1.0);
    clampvector(vec4(color.r*angle, color.g*angle, color.b*angle, color.a), finalColor);
    //finalColor = vec4(vecNormal, 0.0);
    //finalColor = texture(bump, bumpTexCoord);
}
"""

fragshaderSimple = """
#version 330
in vec2 fragTexCoord; //this is the texture coord
in vec3 vecNormal; // normal vector
in vec3 vecBinormal;
in vec3 vecTangent;
in vec2 bumpTexCoord; // coordinates on bump texture

out vec4 finalColor; //this is the output color of the pixel
uniform sampler2D tex;
uniform sampler2D bump;

uniform vec3 light;// = vec3(0.0, 1.0, 0.0);
vec4 ambient = vec4(0.1, 0.1, 0.1, 1.0);

void clampvector(in vec4 vector, out vec4 result) {
    result.x = clamp(vector.x, 0.0, 1.0);
    result.y = clamp(vector.y, 0.0, 1.0);
    result.z = clamp(vector.z, 0.0, 1.0);
    result.w = clamp(vector.w, 0.0, 1.0);
}

void main (void)
{
    //finalColor = vec4(1.0, 1.0, 0.0, 1.0);
    //vec4 color = vec4(fragTexCoord, 1.0, 1.0);
    //finalColor = texture(tex, fragTexCoord);
    vec4 color = texture(tex, fragTexCoord);
    //vec4 color = vec4(0.0, 0.0, 1.0, 1.0);
    if (color.a == 0.0) {
        discard;
    }

    vec3 finalVecNormal = vecNormal;
    finalVecNormal = normalize(finalVecNormal);
    vec3 normlight = normalize(light);

    //float angle = dot(light, vecNormal) * inversesqrt(length(light)) * inversesqrt(length(vecNormal));
    float angle = dot(normlight, finalVecNormal);
    if (length(vecNormal) == 0.0) {
        angle = -1.0;
    }
    angle = clamp((-1*angle+1)/2.0, 0.2, 1.0);
    //float angle = 1.0;
    //finalColor = color*angle;
    //vec4 lightcolor = vec4(1.0, 0.0, 0.0, 1.0);
    clampvector(vec4(color.r*angle, color.g*angle, color.b*angle, color.a), finalColor);
    //clampvector(vec4(0.0, 0.0, 1.0, 1.0), finalColor);
    //finalColor = vec4(vecNormal, 0.0);
    //finalColor = texture(bump, bumpTexCoord);
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


def create_shaderSimple():
    # print(glGetString(GL_VENDOR))
    vertexShaderObject = glCreateShader(GL_VERTEX_SHADER)
    fragmentShaderObject = glCreateShader(GL_FRAGMENT_SHADER)
    # glShaderSource(vertexShaderObject, 1, vertshader, len(vertshader))
    # glShaderSource(fragmentShaderObject, 1, fragshader, len(fragshader))
    glShaderSource(vertexShaderObject, vertshader)
    glShaderSource(fragmentShaderObject, fragshaderSimple)

    _compile_shader_with_error_report(vertexShaderObject)
    _compile_shader_with_error_report(fragmentShaderObject)

    program = glCreateProgram()

    glAttachShader(program, vertexShaderObject)
    glAttachShader(program, fragmentShaderObject)

    glLinkProgram(program)

    return program