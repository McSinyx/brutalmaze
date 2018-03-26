using System;
using System.Text;
using System.Net.Sockets;

namespace BrutalmazeClient
{
	class Program
	{
		static void Main(string[] args)
		{
			const string host = "localhost";
			const int port = 8089;
			Socket client_socket = new Socket(SocketType.Stream, ProtocolType.Tcp);
			client_socket.Connect(host, port);
			Random rnd = new Random();

			int recv, sent;
			byte[] buff = new byte[1000];
			byte[] query;
			string[] matrix = new string[100];
			const int MAGIC = 42; // For escape
			string l, data, l1;
			int sz, nl;
			int nh, ne, nb, score;
			char hC;
			int hX, hY, hA, canAtk, canReg;
			int prevX = 1234, prevY = 5678;
			int dir = 0, deg = 0, atk = 1;
			int needEsc = 0;

			while (42 < 420)
			{
				try
				{
					recv = client_socket.Receive(buff, 7, 0);
				}
				catch (SocketException e)
				{
					Console.WriteLine(e.ToString());
					break;
				}
				l = Encoding.ASCII.GetString(buff, 0, 7);
				sz = Int32.Parse(l);
				if (sz == 0)
					break;
				recv = client_socket.Receive(buff, sz, 0);
				data = Encoding.ASCII.GetString(buff, 0, sz);
				// Standardize Data
				nl = 0;
				l1 = data.Split('\n')[nl];
				nh = Int32.Parse(l1.Split(' ')[0]);
				ne = Int32.Parse(l1.Split(' ')[1]);
				nb = Int32.Parse(l1.Split(' ')[2]);
				score = Int32.Parse(l1.Split(' ')[3]);
				for (int i = 0; i < nh; ++i, ++nl)
					matrix[i] = data.Split('\n')[i + 1];
				l1 = data.Split('\n')[++nl];
				hC = Char.Parse(l1.Split(' ')[0]);
				hX = Int32.Parse(l1.Split(' ')[1]);
				hY = Int32.Parse(l1.Split(' ')[2]);
				hA = Int32.Parse(l1.Split(' ')[3]);
				canAtk = Int32.Parse(l1.Split(' ')[4]);
				canReg = Int32.Parse(l1.Split(' ')[5]);
				for(int i = 1; i <= ne; ++i, ++nl)
				{
				}
				for(int i = 1; i <= nb; ++i, ++nl)
				{
				}
				// Process
				if (needEsc == 0)
				{
					dir = 0;
					if (prevX == hX && prevY == hY)
					{
						int matX = hX / 100, matY = hY / 100;
						if (matrix[matY - 1][matX + 2] == '0' && matrix[matY - 1][matX - 2] == '1')
						{
							dir = 5;
							needEsc = 1;
						}
						if (matrix[matY - 1][matX + 2] == '1' && matrix[matY + 1][matX - 2] == '0')
						{
							dir = 7;
							needEsc = 1;
						}
					}
				}
				else
				{
					needEsc = (needEsc + 1) % MAGIC;
				}
				deg = rnd.Next(-4, 5) * 10;
				atk = rnd.Next(1, 1);
				query = Encoding.ASCII.GetBytes(dir.ToString() + " " + deg.ToString() + " " + atk.ToString());
				sent = client_socket.Send(query);
				prevX = hX;
				prevY = hY;
			}
			client_socket.Shutdown(SocketShutdown.Both);
			client_socket.Close();
		}
	}
}