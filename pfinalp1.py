#!/usr/bin/python
# -*- coding: utf-8 -*-
import sys
from subprocess import call
from lxml import etree
import copy
from time import sleep

pwd = ""

def crearLb():
	#Se crea su archivo qcow2 y su archivo de configuracion
	call("qemu-img create -f qcow2 -b cdps-vm-base-p3.qcow2 practicaFinalLb.qcow2", shell = True)
	call("cp plantilla-vm-p3.xml lb.xml", shell = True)

	#Se modifica su archivo de configuracion para ponerle el nombre, su archivo qcow2 y crear y configurar sus interfaces
	tree = etree.parse("lb.xml")
	root = tree.getroot()
	name = root.find("name")
	name.text = "lb"
	source = root.find("./devices/disk/source")
	source.set("file", pwd + "practicaFinalLb.qcow2")
	sourceLan1 = root.find("./devices/interface/source")
	sourceLan1.set("bridge", "LAN1")
	interface = root.find("./devices/interface")
	interface2 = copy.deepcopy(interface)
	sourceLan2 = interface2.find("source")
	sourceLan2.set("bridge", "LAN2")
	tree.find("devices").append(interface2)
	tree.write("lb.xml")  #Se guardan los cambios




def crearC1():
	#Se crea su archivo qcow2 y su archivo de configuracion
	call("qemu-img create -f qcow2 -b cdps-vm-base-p3.qcow2 practicaFinalC1.qcow2", shell = True)
	call("cp plantilla-vm-p3.xml c1.xml", shell = True)
	#Se parsea su archivo de configuracion y se modifica lo necesario
	tree = etree.parse("c1.xml")
	root = tree.getroot()
	name = root.find("name")
	name.text = "c1"
	source = root.find("./devices/disk/source")
	source.set("file", pwd + "practicaFinalC1.qcow2")
	interface = root.find("./devices/interface/source")
	interface.set("bridge", "LAN1")
	tree.write("c1.xml")




def balanceador(algoritmo):

	#Se configura el balanceador
	#Se lee el numero de MV arrancadas
	f1 = open("MVarrancadas.txt","r")
	for line in f1:
		numeroMaquinas = line
		break
	f1.close()
	#El inicio del comando
	comando = "xr " + algoritmo + " --server tcp:0:80"

	#En funcion del numero de MV creadas se genera el comando
	for l in range(1, int(numeroMaquinas) + 1):
		comando = comando + ' --backend 10.0.2.1' + str(l) + ':80'
	#Se escribe el final del comando
	comando = comando + ' --web-interface 0:8001&'
	#Se apaga el servidor apache que tiene el lb
	#call("echo service apache2 stop >> mnt/etc/rc.local" , shell = True)
	#Se añade el comando a rc.local sin borrar lo ya escrito
	#call("echo " +comando+ " >> mnt/etc/rc.local" , shell = True)
	#call("echo exit 0 >> mnt/etc/rc.local" , shell = True)
	f2 = open("./mnt/etc/rc.local","w")
	f2.write("#!/bin/sh -e\nservice apache2 stop\n"+ comando +"\nexit 0\n")
	f2.close()			




def crear():
	#Se establece el numero de maquinas virtuales(servidores) por defecto
	numero = 2
	#Si se dice cuantas maquinas virtuales concretamente arrancar
	if(len(sys.argv) > 2):
		#y se comprueba que el numero va de 1 a 5
		if(int(sys.argv[2]) > 0 and int(sys.argv[2]) < 6):
			#Se actualiza el numero de MV a arrancar
			numero = int(sys.argv[2])
		#Si el numero no es correcto se imprime por consola un error y se detiene la ejecucion del programa
		else:
			print("Numero de maquinas a arrancar incorrecto")
			return
	#Se hace un bucle que itere tantas veces como MV se quiera arrancar
	for l in range(1, numero + 1):
		#Se crea su archivo qcow2 y su archivo de configuracion
		call("qemu-img create -f qcow2 -b cdps-vm-base-p3.qcow2 practicaFinal" + str(l) + ".qcow2", shell = True)
		call("cp plantilla-vm-p3.xml s" + str(l) + ".xml", shell = True)
		#Se parsea su archivo de configuracion y se modifica lo necesario
		tree = etree.parse("s"+str(l)+".xml")
		root = tree.getroot()
		name = root.find("name")
		name.text = "s"+ str(l)
		source = root.find("./devices/disk/source")
		source.set("file", pwd + "practicaFinal" + str(l) + ".qcow2")
		interface = root.find("./devices/interface/source")
		interface.set("bridge", "LAN2")
		#Se guardan los cambios
		tree.write("s"+str(l)+".xml")
	#Se guarda en un fichero de texto el nº de MV arrancadas
	call("echo " + str(numero) + " > MVarrancadas.txt", shell= True)
	crearLb()
	crearC1()
	#Se configura la red para soportar la conectividad, creando las lans y conectando el host a la red virtual
	call("sudo brctl addbr LAN1", shell= True)
	call("sudo brctl addbr LAN2", shell= True)
	call("sudo ifconfig LAN1 up", shell= True)
	call("sudo ifconfig LAN2 up", shell= True)
	call("sudo ifconfig LAN1 10.0.1.3/24", shell= True)
	call("sudo ip route add 10.0.0.0/16 via 10.0.1.1", shell= True)
	
	
	#Se crea la carpeta donde se montaran los discos de las MV
	call("mkdir mnt", shell = True)


	#LB
	#Se monta en mnt el lb
	call("sudo vnx_mount_rootfs -s -r practicaFinalLb.qcow2 mnt", shell = True)
	sleep(1) #Tiempo de guarda para que le de tiempo a montarse
	#Se edita el nombre de la maquina
	call("echo lb > mnt/etc/hostname" , shell = True)
	call("sed -i 's/cdps cdps/lb/' mnt/etc/hosts", shell = True)
	#Se le configuran la interfazes eth0 y eth2 para conectar las MV
	balanceador("")
	call("cp mnt/etc/network/interfaces .", shell = True)
	auxiliar = open("interfaces", "r")
	interfaces = open("mnt/etc/network/interfaces", "w")
	for line in auxiliar:
		if "iface lo inet loopback" in line:
			interfaces.write(line + "\n" + "auto eth1" + "\n" +"iface eth1 inet static" +"\n" + "address 10.0.2.1"+ "\n" + "netmask 255.255.255.0" + "\n" + "network 10.0.2.0" + "\n" + "broadcast 10.0.2.255" + "\n" + "auto eth0" + "\n" + "iface eth0 inet static"+"\n" + "address 10.0.1.1"+ "\n" + "netmask 255.255.255.0" + "\n" + "network 10.0.1.0" + "\n" + "broadcast 10.0.1.255" + "\n")
		else:
			interfaces.write(line)
	interfaces.close()
	auxiliar.close()
	#Se elimina el archivo auxiliar
	call("rm ./interfaces", shell= True)
	#Se le configura como router
	call("sed -i 's/#net.ipv4.ip_forward=1/net.ipv4.ip_forward=1/' mnt/etc/sysctl.conf" , shell = True)
	#Se desmonta el disco
	call("sudo vnx_mount_rootfs -u mnt", shell = True)
	#Se le asigna el archivo de configuracion
	call("sudo virsh define lb.xml", shell= True)



	#C1
	#Se monta en mnt c1
	call("sudo vnx_mount_rootfs -s -r practicaFinalC1.qcow2 mnt", shell = True)
	sleep(1)
	#call('echo "#!/usr/bin/python\nimport sys\nfrom subprocess import call\ncall(\'curl 10.0.1.1\', shell = True)\n" > mnt/home/cdps/trafico.py' , shell = True)
	call("sed -i 's/cdps cdps/c1/' mnt/etc/hosts", shell = True)
	call("echo c1 > mnt/etc/hostname" , shell = True)
	call("cp mnt/etc/network/interfaces .", shell = True)
	auxiliar = open("interfaces", "r")
	interfaces = open("mnt/etc/network/interfaces", "w")
	for line in auxiliar:
		if "iface lo inet loopback" in line:
			interfaces.write(line + "\n" + "auto eth0" + "\n" +"iface eth0 inet static" +"\n" + "address 10.0.1.2"+ "\n" + "netmask 255.255.255.0" + "\n" + "network 10.0.1.0" + "\n" + "broadcast 10.0.1.255" + "\n" + "gateway 10.0.1.1")
		else:
			interfaces.write(line)
	interfaces.close()
	auxiliar.close()
	call("rm ./interfaces", shell= True)
	call("sudo vnx_mount_rootfs -u mnt", shell = True)
	call("sudo virsh define c1.xml", shell= True)



	#SERVIDORES
	#Se leen cuantas maquinas virtuales hay arrancadas
	f1 = open("MVarrancadas.txt","r")
	for line in f1:
		numeroMaquinas = line
		break
	f1.close()
	for l in range(1, int(numeroMaquinas) + 1):

		call("sudo vnx_mount_rootfs -s -r practicaFinal" + str(l) + ".qcow2 mnt", shell = True)
		sleep(1)
		call("sed -i 's/cdps cdps/s" + str(l) +"/' mnt/etc/hosts", shell = True)
		call("echo s" + str(l) + " > mnt/etc/hostname" , shell = True)
		#Modificar las configuraciones

		call("cp mnt/etc/network/interfaces .", shell = True)
		auxiliar = open("interfaces", "r")
		interfaces = open("mnt/etc/network/interfaces", "w")
		for line in auxiliar:
			if "iface lo inet loopback" in line:
				interfaces.write(line + "\n" + "auto eth0" + "\n" +"iface eth0 inet static" +"\n" + "address 10.0.2."+str(l+10)+""+ "\n" + "netmask 255.255.255.0" + "\n" + "network 10.0.2.0" + "\n" + "broadcast 10.0.2.255" + "\n" + "gateway 10.0.2.1")
			else:
				interfaces.write(line)
		interfaces.close()
		auxiliar.close()
		call("rm ./interfaces", shell= True)
		#Se les cambia el index.html para que muestren su nombre si un navegador accede a su ip
		call("echo s" + str(l) + " > mnt/var/www/html/index.html", shell = True)
		call("sudo vnx_mount_rootfs -u mnt", shell = True)
		call("sudo virsh define s" + str(l) + ".xml" , shell = True)
	call("rm -Rf mnt", shell = True)
	
		

def arrancar():

	#En principio si no se mete ningun parametro se arrancan todas las MV
	nombre = "todas"
	#Si se escribe un tercer parametro, es decir, ./pfinalp1.py arrancar <nombreMV>
	if(len(sys.argv) > 2 and len(sys.argv) < 4):
		#Se guarda el nombre de la MV a arrancar
		nombre = sys.argv[2]
	#Se leen cuantas maquinas se crearon
	f1 = open("MVarrancadas.txt","r")
	for line in f1:
		numeroMaquinas = line
		break
	f1.close()
	#Si no se especifica nombre de MV a arrancar se arrancan todas
	if (nombre == "todas"):
		#Se abre el virt-manager
		call("sudo virt-manager&" , shell = True)
		#Se arranca lb
		arrancarVM("lb")
		#Se arranca c1
		arrancarVM("c1")
		#Se arrancan los servidores
		for l in range(1, int(numeroMaquinas) + 1):
			arrancarVM("s"+str(l))

	#Si se especifica la maquina a arrancar se arranca solo esa
	#Comprobando que no se intenta arrancar una maquina que no ha sido creada previamente
	elif (nombre == "s1"):
		call("sudo virt-manager&" , shell = True)
		arrancarVM(nombre)		
	elif (nombre == "s2" and int(numeroMaquinas) >= 2):
		call("sudo virt-manager&" , shell = True)
		arrancarVM(nombre)
	elif (nombre == "s3" and int(numeroMaquinas) >= 3):
		call("sudo virt-manager&" , shell = True)
		arrancarVM(nombre)
	elif (nombre == "s4" and int(numeroMaquinas) >= 4):
		call("sudo virt-manager&" , shell = True)
		arrancarVM(nombre)
	elif (nombre == "s5" and int(numeroMaquinas) == 5):
		call("sudo virt-manager&" , shell = True)
		arrancarVM(nombre)
	elif (nombre == "lb"):
		call("sudo virt-manager&" , shell = True)
		arrancarVM(nombre)
	elif (nombre == "c1"):
		call("sudo virt-manager&" , shell = True)
		arrancarVM(nombre)
	else:
		print("Nombre de maquina incorrecto o no creada")
	


def arrancarVM(nombreMaquina):
	#Se arranca la maquina virtual en cuestion
	call("sudo virsh start " + nombreMaquina , shell = True)
	#Se le abre una consola en background
	call('xterm -e "sudo virsh console ' + nombreMaquina + '"&', shell = True)



#Analogo a arrancar
def parar():
	nombre = "todas"
	if(len(sys.argv) > 2 and len(sys.argv) < 4):
		nombre = sys.argv[2]
	f1 = open("MVarrancadas.txt","r")
	for line in f1:
		numeroMaquinas = line
		break
	f1.close()
	if (nombre == "todas"):
		pararVM("lb")
		pararVM("c1")
		for l in range(1, int(numeroMaquinas) + 1):
			pararVM("s"+ str(l))
	elif (nombre == "s1"):
		pararVM(nombre)		
	elif (nombre == "s2" and int(numeroMaquinas) >= 2):
		pararVM(nombre)
	elif (nombre == "s3" and int(numeroMaquinas) >= 3):
		pararVM(nombre)
	elif (nombre == "s4" and int(numeroMaquinas) >= 4):
		pararVM(nombre)
	elif (nombre == "s5" and int(numeroMaquinas) == 5):
		pararVM(nombre)
	elif (nombre == "lb"):
		pararVM(nombre)
	elif (nombre == "c1"):
		pararVM(nombre)
	else:
		print("Nombre de maquina incorrecto o no creada")



def pararVM(nombreMaquina):
	#Se apaga la MV
	call("sudo virsh shutdown " + nombreMaquina, shell = True)
	



	#Se destruyen todas las MV y se desconfiguran del virt-manager
def destruir():

	#Se destruye lb
	call("sudo virsh destroy lb", shell = True)
	call("sudo virsh undefine lb", shell = True)
	
	#Se destruye c1
	call("sudo virsh destroy c1", shell = True)
	call("sudo virsh undefine c1", shell = True)

	f1 = open("MVarrancadas.txt","r")
	for line in f1:
		numeroMaquinas = line
		break
	f1.close()

	for l in range(1, int(numeroMaquinas) + 1):
		#Se destruyen los servidores creados
		call("sudo virsh destroy s" + str(l), shell = True)
		call("sudo virsh undefine s" + str(l), shell = True)

	#Se borran los .qcow2 asociados a cada MV
	call("rm -f practicaFinal*" , shell = True)
	#Se borran los .xml asociados a cada MV
	call("rm -f s*" , shell = True)
	call("rm -f lb.xml" , shell = True)
	call("rm -f c1.xml" , shell = True)
	#Se borra el archivo MVarrancadas.txt
	call("rm -f MV*" , shell = True)
	#call("rm -f MV*" , shell = True)



def monitor():
	#Se monitoriza cada 1 segundo el estado de las MV en una nueva terminal
	
	if(len(sys.argv) > 2):
		nombre = sys.argv[2]
		call('gnome-terminal -e "watch -n 1 -d sudo virsh cpu-stats ' + nombre + '"' , shell = True)
	else:
		call('gnome-terminal -e "watch -n 1 -d sudo virsh list"' , shell = True)



#Se averigua la localizacion del archivo .qcow2
call("pwd > localizacion.txt", shell = True)
f2 = open("localizacion.txt","r")
for line in f2:
	pwd = line
	break
f2.close()
call("rm localizacion.txt", shell = True)
#Se elimina un salto de linea que introduce el pwd
pwd = pwd.replace('\n', '/')
#print (str(pwd))



def generarTrafico():
	if(len(sys.argv) > 2):
		nombre = sys.argv[2]
	else:
		nombre = ""

	if(nombre == "s1"):
		#Se genera trafico desde el host al c1
		call("while true; do curl 10.0.2.11; sleep 0.1; done", shell = True)
	if(nombre == "s2"):
		#Se genera trafico desde el host al c1
		call("while true; do curl 10.0.2.12; sleep 0.1; done", shell = True)
	if(nombre == "s3"):
		#Se genera trafico desde el host al c1
		call("while true; do curl 10.0.2.13; sleep 0.1; done", shell = True)
	if(nombre == "s3"):
		#Se genera trafico desde el host al c1
		call("while true; do curl 10.0.2.14; sleep 0.1; done", shell = True)
	if(nombre == "s5"):
		#Se genera trafico desde el host al c1
		call("while true; do curl 10.0.2.15; sleep 0.1; done", shell = True)
	else:
		#Se genera trafico desde el host al c1
		call("while true; do curl 10.0.1.1; sleep 0.1; done", shell = True)




def ayuda():
	if(len(sys.argv) > 2):
		nombre = sys.argv[2]
	else:
		nombre = ""

	if(nombre == "crear"):
		call("clear", shell = True)
		print("\nCrea tantas maquinas virtuales como se le especifique con crear <numeroMaquinas>\n")
		print("Si no se especifica numero se crearan 2\n")
		print("Como maximo se pueden crear 5\n")

	elif(nombre == "arrancar"):
		call("clear", shell = True)
		print("\nArranca todas las maquinas virtuales creadas, o la especificada, con arrancar <NombreMaquina>\n")

	elif(nombre == "parar"):
		call("clear", shell = True)
		print("\nDetiene todas las maquinas virtuales, o la especificada, con parar <NombreMaquina>\n")

	elif(nombre == "destruir"):
		call("clear", shell = True)
		print("\nDestruye todas las maquinas virtuales\n")

	elif(nombre == "monitor"):
		call("clear", shell = True)
		print("\nMonitoriza el estado de las maquinas virtuales, escribe monitor <NombreMaquina>\n")

	elif(nombre == "trafico"):
		call("clear", shell = True)
		print('\nGenera trafico en la red desde el host hacia el servidor especificado, por defecto es el lb \n')

	elif(nombre == "balanceado"):
		call("clear", shell = True)
		print("\nSelecciona el algoritmo del balanceador, escribiendo balanceado <Algoritmo de balanceo> \n")
		print("En <Algoritmo de balanceo> se puede escribir round-robin, first-available o least-connections \n")

	else:
		call("clear", shell = True)
		print("\nLos comandos disponibles son crear, arrancar, parar, destruir, monitor, balanceado y trafico \n")	
		print('Si quieres mas informacion de uno en concreto, escribe "-help <comando>" \n')


def selectorAlgoritmo():
	if(len(sys.argv) > 2):
		algoritmo = sys.argv[2]
	else:
		algoritmo = ""
	
	algoritmo2 = ""
	call("ssh root@10.0.1.1 service apache2 stop", shell = True)
	
	if (algoritmo == "round-robin"):
		algoritmo2 = "-dr"

	elif (algoritmo == "first-available"):
		algoritmo2 = "-df"

	elif (algoritmo == "least-connections"):
		algoritmo2 = "-dl"

	else:
		print('Comando introducido no valido, escribe "-help balanceado" si necesitas ayuda')
		return
	comando = "ssh root@10.0.1.1 xr " + algoritmo2 + " --server tcp:0:80"
	f1 = open("MVarrancadas.txt","r")
	for line in f1:
		numeroMaquinas = line
		break
	f1.close()
	for l in range(1, int(numeroMaquinas) + 1):
		comando = comando + ' --backend 10.0.2.1' + str(l) + ':80'
	comando = comando + ' --web-interface 0:8001'

	call("sudo virsh destroy lb", shell = True)
	call("sudo virsh undefine lb", shell = True)
	call("rm -f practicaFinalLb.qcow2" , shell = True)
	call("rm -f lb.xml" , shell = True)
	crearLb()
	call("mkdir mnt", shell = True)
	call("sudo vnx_mount_rootfs -s -r practicaFinalLb.qcow2 mnt", shell = True)
	sleep(1) #Tiempo de guarda para que le de tiempo a montarse
	#Se edita el nombre de la maquina
	call("echo lb > mnt/etc/hostname" , shell = True)
	call("sed -i 's/cdps cdps/lb/' mnt/etc/hosts", shell = True)
	#Se le configuran la interfazes eth0 y eth2 para conectar las MV
	balanceador(algoritmo2)
	call("cp mnt/etc/network/interfaces .", shell = True)
	auxiliar = open("interfaces", "r")
	interfaces = open("mnt/etc/network/interfaces", "w")
	for line in auxiliar:
		if "iface lo inet loopback" in line:
			interfaces.write(line + "\n" + "auto eth1" + "\n" +"iface eth1 inet static" +"\n" + "address 10.0.2.1"+ "\n" + "netmask 255.255.255.0" + "\n" + "network 10.0.2.0" + "\n" + "broadcast 10.0.2.255" + "\n" + "auto eth0" + "\n" + "iface eth0 inet static"+"\n" + "address 10.0.1.1"+ "\n" + "netmask 255.255.255.0" + "\n" + "network 10.0.1.0" + "\n" + "broadcast 10.0.1.255" + "\n")
		else:
			interfaces.write(line)
	interfaces.close()
	auxiliar.close()
	#Se elimina el archivo auxiliar
	call("rm ./interfaces", shell= True)
	#Se le configura como router
	call("sed -i 's/#net.ipv4.ip_forward=1/net.ipv4.ip_forward=1/' mnt/etc/sysctl.conf" , shell = True)
	#Se desmonta el disco
	call("sudo vnx_mount_rootfs -u mnt", shell = True)
	call("rm -rf mnt", shell = True)
	#Se le asigna el archivo de configuracion
	call("sudo virsh define lb.xml", shell= True)
	arrancarVM("lb")
	#print(comando)
	#call(comando, shell = True)

	
#Se comprueba que se haya introducido al menos 1 argumento
if(len(sys.argv) > 1):
	#Se asigna el argumento a la variable orden
	orden = sys.argv[1]
	#En funcion del string se llama a un metodo u otro
	if (orden == "crear"):
		crear()
	elif (orden == "arrancar"):
		arrancar()
	elif (orden == "parar"):
		parar()
	elif (orden == "destruir"):
		destruir()
	elif (orden == "monitor"):
		monitor()
	elif (orden == "trafico"):
		generarTrafico()
	elif (orden == "-help"):
		ayuda()
	elif (orden == "balanceado"):
		selectorAlgoritmo()
	else: 
		#Si no es ningun argumento conocido informa al usuario
		print("introduce argumento valido, escribe -help si necesitas ayuda")
	
else: 
	#Si no se introduce argumento informa al usuario
	print("introduce argumento, escribe -help si necesitas ayuda")

	


